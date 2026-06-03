"""Zamanlanmis tarama dispatcher'i (Celery beat tarafindan periyodik calistirilir).

`core.scan_due_monitors` gorevi her N saniyede (settings.scan_beat_interval_seconds)
calisir; aktif ve vadesi gelmis (scan_interval_minutes'a gore) tum monitorler icin bir
Task olusturup genel `run_module_scan` gorevini kuyruga atar ve monitorun
last_scanned_at degerini gunceller (boylece bir sonraki beat'te tekrar tetiklenmez).

Modulden bagimsizdir: tek dispatcher 9 modulun tum monitorlerine hizmet eder.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.sync_db import SyncSessionLocal
from app.core_services.queue.celery_app import celery_app
from app.core_services.queue.scheduling import is_report_due, select_due_monitors
from app.models.finding import Finding
from app.models.monitor import Monitor
from app.models.task import Task, TaskStatus
from app.models.tenant import Organization


@celery_app.task(name="core.scan_due_monitors")
def scan_due_monitors() -> dict:
    """Vadesi gelmis tum aktif monitorleri tarar (her modul icin)."""
    # Geç import: dairesel bagimliligi onle
    from app.core_services.queue.scan_tasks import run_module_scan

    now = datetime.now(timezone.utc)
    dispatched = 0

    with SyncSessionLocal() as db:
        candidates = db.execute(
            select(Monitor).where(
                Monitor.is_active.is_(True),
                Monitor.scan_interval_minutes.isnot(None),
            )
        ).scalars().all()

        for monitor in select_due_monitors(candidates, now):
            task = Task(
                organization_id=monitor.organization_id,
                monitor_id=monitor.id,
                module_key=monitor.module_key,
                status=TaskStatus.PENDING,
            )
            db.add(task)
            db.flush()  # task.id

            # last_scanned_at'i enqueue aninda guncelle: uzun suren tarama olsa bile
            # bir sonraki beat ayni monitoru yeniden tetiklemesin (yarist onleme).
            monitor.last_scanned_at = now

            try:
                async_result = run_module_scan.delay(str(task.id), str(monitor.id))
                task.celery_task_id = async_result.id
            except Exception:
                # Broker erisilemezse Task PENDING kalir; bir sonraki beat tekrar dener
                pass
            dispatched += 1

        db.commit()

    return {"dispatched": dispatched, "at": now.isoformat()}


@celery_app.task(name="core.send_scheduled_reports")
def send_scheduled_reports() -> dict:
    """Zamanlanmis (gunluk/haftalik) PDF raporlari e-posta ile gonderir."""
    # Geç import: weasyprint/notifications agir bagimliliklar
    from app.core_services.notifications.engine import send_email_with_attachment
    from app.outputs.pdf import render_findings_pdf

    now = datetime.now(timezone.utc)
    sent = 0
    with SyncSessionLocal() as db:
        orgs = db.execute(select(Organization)).scalars().all()
        for org in orgs:
            if not org.notify_email or not is_report_due(
                org.report_schedule, org.last_report_at, now
            ):
                continue
            findings = (
                db.execute(
                    select(Finding)
                    .where(Finding.organization_id == org.id)
                    .order_by(Finding.detected_at.desc())
                )
                .scalars()
                .all()
            )
            try:
                pdf = render_findings_pdf(org.name, findings)
                ok = send_email_with_attachment(
                    org.notify_email,
                    f"[Argus] {org.report_schedule} rapor - {now.date().isoformat()}",
                    "Ekte zamanlanmis Argus istihbarat raporunuz yer almaktadir.",
                    "argus-rapor.pdf",
                    pdf,
                )
            except Exception:
                ok = False
            # Basarisiz olsa bile last_report_at ilerlet: her dakika tekrar denemesin
            org.last_report_at = now
            if ok:
                sent += 1
        db.commit()
    return {"sent": sent, "at": now.isoformat()}
