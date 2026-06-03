"""Genel (modulden bagimsiz) tarama Celery gorevi.

Herhangi bir modul icin calisir: monitor'un module_key'ine gore kayit defterinden
modulu bulur, scan() + analyze() calistirir, Finding kaydeder ve bildirim gonderir.
Boylece her yeni modul icin ayri bir gorev yazmaya gerek kalmaz.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.sync_db import SyncSessionLocal
from app.core.utils import finding_fingerprint, severity_at_least
from app.core_services.notifications.engine import OutputChannels, notify_finding
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


def _channels_for(org: Organization | None) -> OutputChannels:
    """Kurumun yapilandirilmis cikti kanallarini toplar (None => bos kanal seti)."""
    if org is None:
        return OutputChannels()
    return OutputChannels(
        webhook_url=org.webhook_url,
        slack_webhook_url=org.slack_webhook_url,
        github_repo=org.github_repo,
        github_token=org.github_token,
        jira_base_url=org.jira_base_url,
        jira_email=org.jira_email,
        jira_token=org.jira_token,
        jira_project_key=org.jira_project_key,
        email_to=org.notify_email,
        gov_report_url=org.gov_report_url,
        gov_report_token=org.gov_report_token,
    )


@celery_app.task(name="core.run_module_scan")
def run_module_scan(task_id: str, monitor_id: str) -> dict:
    """Bir monitor icin (modulune gore) tarama calistirir, bulgulari kaydeder ve bildirir."""
    load_modules()  # worker surecinde modullerin kayitli oldugundan emin ol
    findings_count = 0
    updated_count = 0

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
            channels = _channels_for(org)

            for result in scan_results:
                triaged = module.analyze(result, monitor)
                now = datetime.now(timezone.utc)
                fingerprint = finding_fingerprint(
                    monitor.module_key, monitor.id, result.raw_data
                )

                existing = db.execute(
                    select(Finding).where(
                        Finding.monitor_id == monitor.id,
                        Finding.fingerprint == fingerprint,
                    )
                ).scalar_one_or_none()

                if existing is not None:
                    # Ayni bulgu yeniden gorundu: cogaltma; say ve guncelle (re-triyaj degisebilir)
                    existing.seen_count += 1
                    existing.last_seen_at = now
                    existing.severity = _to_severity(triaged.severity)
                    existing.summary = triaged.summary
                    existing.recommendation = triaged.recommendation
                    updated_count += 1
                    continue

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
                        fingerprint=fingerprint,
                        seen_count=1,
                        last_seen_at=now,
                    )
                )
                findings_count += 1

                # Bildirim: yalnizca YENI ve esik (notify_min_severity) ustu bulgular icin
                if (
                    channels.any_configured()
                    and severity_at_least(triaged.severity, settings.notify_min_severity)
                ):
                    notify_finding(
                        title=triaged.title,
                        severity=triaged.severity,
                        summary=triaged.summary,
                        recommendation=triaged.recommendation,
                        asset_value=result.asset_value,
                        module_key=monitor.module_key,
                        channels=channels,
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

    return {
        "task_id": task_id,
        "findings": findings_count,  # yeni olusturulan
        "updated": updated_count,  # tekrar gorulup guncellenen
        "module": monitor.module_key,
    }
