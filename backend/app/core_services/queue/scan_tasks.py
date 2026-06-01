"""Genel (modulden bagimsiz) tarama Celery gorevi.

Herhangi bir modul icin calisir: monitor'un module_key'ine gore kayit defterinden
modulu bulur, scan() + analyze() calistirir, Finding kaydeder ve bildirim gonderir.
Boylece her yeni modul icin ayri bir gorev yazmaya gerek kalmaz.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from app.core.sync_db import SyncSessionLocal
from app.core_services.notifications.engine import notify_finding
from app.core_services.queue.celery_app import celery_app
from app.models.finding import Finding, FindingSeverity
from app.models.monitor import Monitor
from app.models.task import Task, TaskStatus
from app.models.tenant import Organization
from app.modules import load_modules
from app.modules.base import get_module


def _to_severity(value: str) -> FindingSeverity:
    try:
        return FindingSeverity(value)
    except ValueError:
        return FindingSeverity.MEDIUM


@celery_app.task(name="core.run_module_scan")
def run_module_scan(task_id: str, monitor_id: str) -> dict:
    """Bir monitor icin (modulune gore) tarama calistirir, bulgulari kaydeder ve bildirir."""
    load_modules()  # worker surecinde modullerin kayitli oldugundan emin ol
    findings_count = 0

    with SyncSessionLocal() as db:
        task = db.get(Task, uuid.UUID(task_id))
        monitor = db.get(Monitor, uuid.UUID(monitor_id))
        if task is None or monitor is None:
            return {"error": "task veya monitor bulunamadi"}

        module = get_module(monitor.module_key)
        if module is None:
            task.status = TaskStatus.FAILED
            task.error = f"Modul bulunamadi: {monitor.module_key}"
            task.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {"error": task.error}

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            scan_results = asyncio.run(module.scan(monitor))
            org = db.get(Organization, monitor.organization_id)

            for result in scan_results:
                triaged = module.analyze(result, monitor)
                db.add(
                    Finding(
                        organization_id=monitor.organization_id,
                        monitor_id=monitor.id,
                        module_key=monitor.module_key,
                        title=triaged.title,
                        severity=_to_severity(triaged.severity),
                        summary=triaged.summary,
                        recommendation=triaged.recommendation,
                        source=result.source,
                        asset_value=result.asset_value,
                        raw_data=result.raw_data,
                    )
                )
                findings_count += 1

                if org and (org.webhook_url or org.slack_webhook_url):
                    notify_finding(
                        title=triaged.title,
                        severity=triaged.severity,
                        summary=triaged.summary,
                        asset_value=result.asset_value,
                        webhook_url=org.webhook_url,
                        slack_webhook_url=org.slack_webhook_url,
                    )

            task.status = TaskStatus.DONE
            task.findings_count = findings_count
            task.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            task = db.get(Task, uuid.UUID(task_id))
            if task:
                task.status = TaskStatus.FAILED
                task.error = str(exc)[:2000]
                task.finished_at = datetime.now(timezone.utc)
                db.commit()
            raise

    return {"task_id": task_id, "findings": findings_count, "module": monitor.module_key}
