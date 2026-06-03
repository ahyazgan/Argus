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
from app.core_services.queue.scheduling import select_due_monitors
from app.models.monitor import Monitor
from app.models.task import Task, TaskStatus


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
