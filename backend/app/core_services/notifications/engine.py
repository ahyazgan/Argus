"""Bildirim motoru - yeni bulguda webhook/Slack ve e-posta gonderir.

Senkron (Celery gorevi icinden cagrilir). Yapilandirilmamis kanallar sessizce atlanir.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import settings

_SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}


def _slack_payload(title: str, severity: str, summary: str, asset_value: str) -> dict:
    emoji = _SEVERITY_EMOJI.get(severity, "⚪")
    return {
        "text": f"{emoji} *Argus uyarisi* — {title}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *{title}*\n"
                        f"*Onem:* {severity.upper()}  |  *Varlik:* `{asset_value}`\n"
                        f"{summary}"
                    ),
                },
            }
        ],
    }


def send_webhook(url: str, payload: dict) -> bool:
    try:
        resp = httpx.post(url, json=payload, timeout=10.0)
        return resp.is_success
    except httpx.HTTPError:
        return False


def send_email(to_addr: str, subject: str, body: str) -> bool:
    if not settings.smtp_host:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_addr
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False


def notify_finding(
    *,
    title: str,
    severity: str,
    summary: str,
    asset_value: str,
    webhook_url: str | None = None,
    slack_webhook_url: str | None = None,
) -> dict:
    """Bir bulgu icin yapilandirilmis kanallara bildirim gonderir."""
    results: dict[str, bool] = {}
    if slack_webhook_url:
        results["slack"] = send_webhook(
            slack_webhook_url, _slack_payload(title, severity, summary, asset_value)
        )
    if webhook_url:
        results["webhook"] = send_webhook(
            webhook_url,
            {
                "event": "finding.created",
                "title": title,
                "severity": severity,
                "summary": summary,
                "asset_value": asset_value,
            },
        )
    return results
