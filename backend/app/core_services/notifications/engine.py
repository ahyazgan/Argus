"""Bildirim / cikti motoru - yeni bulguda yapilandirilmis kanallara gonderir.

Kanallar: Slack, genel webhook, GitHub Issue, Jira Issue, e-posta. Senkron (Celery
gorevi icinden cagrilir). Yapilandirilmamis kanallar sessizce atlanir; bir kanalin
hatasi digerlerini etkilemez.
"""
from __future__ import annotations

import base64
import smtplib
from dataclasses import dataclass
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
# GitHub etiketi / Jira oncelik eslemesi
_JIRA_PRIORITY = {
    "critical": "Highest",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "info": "Lowest",
}


@dataclass
class OutputChannels:
    """Bir kurumun yapilandirilmis cikti kanallari (None => devre disi)."""

    webhook_url: str | None = None
    slack_webhook_url: str | None = None
    github_repo: str | None = None  # "owner/repo"
    github_token: str | None = None
    jira_base_url: str | None = None  # "https://firma.atlassian.net"
    jira_email: str | None = None
    jira_token: str | None = None
    jira_project_key: str | None = None
    email_to: str | None = None

    def any_configured(self) -> bool:
        return any(
            [
                self.webhook_url,
                self.slack_webhook_url,
                self.github_repo and self.github_token,
                self.jira_base_url and self.jira_token and self.jira_project_key,
                self.email_to,
            ]
        )


# --- Payload kurucular (saf, test edilebilir) ---

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


def github_issue_payload(
    title: str, severity: str, summary: str, recommendation: str | None, asset_value: str
) -> dict:
    """GitHub Issue govdesi (Markdown) + onem etiketi."""
    body = (
        f"**Önem:** {severity.upper()}\n"
        f"**Varlık:** `{asset_value}`\n\n"
        f"{summary or ''}\n"
    )
    if recommendation:
        body += f"\n**Önerilen aksiyon:** {recommendation}\n"
    body += "\n— Argus Intelligence tarafından otomatik oluşturuldu."
    return {"title": f"[Argus] {title}", "body": body, "labels": ["argus", f"severity:{severity}"]}


def jira_issue_payload(
    project_key: str,
    title: str,
    severity: str,
    summary: str,
    recommendation: str | None,
    asset_value: str,
) -> dict:
    """Jira REST v3 'issue create' govdesi (ADF degil, sade metin alani)."""
    desc = f"Önem: {severity.upper()}\nVarlık: {asset_value}\n\n{summary or ''}"
    if recommendation:
        desc += f"\n\nÖnerilen aksiyon: {recommendation}"
    return {
        "fields": {
            "project": {"key": project_key},
            "summary": f"[Argus] {title}"[:254],
            "description": desc,
            "issuetype": {"name": "Task"},
            "priority": {"name": _JIRA_PRIORITY.get(severity, "Medium")},
        }
    }


# --- Gondericiler ---

def send_webhook(url: str, payload: dict) -> bool:
    try:
        resp = httpx.post(url, json=payload, timeout=10.0)
        return resp.is_success
    except httpx.HTTPError:
        return False


def create_github_issue(repo: str, token: str, payload: dict) -> bool:
    """GitHub Issue olusturur (repo: 'owner/repo')."""
    try:
        resp = httpx.post(
            f"https://api.github.com/repos/{repo}/issues",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )
        return resp.is_success
    except httpx.HTTPError:
        return False


def create_jira_issue(base_url: str, email: str, token: str, payload: dict) -> bool:
    """Jira Cloud Issue olusturur (Basic auth: email:api_token)."""
    try:
        auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        resp = httpx.post(
            f"{base_url.rstrip('/')}/rest/api/3/issue",
            json=payload,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            timeout=15.0,
        )
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
    recommendation: str | None = None,
    channels: OutputChannels,
) -> dict:
    """Bir bulgu icin tum yapilandirilmis kanallara bildirim/ticket gonderir."""
    results: dict[str, bool] = {}

    if channels.slack_webhook_url:
        results["slack"] = send_webhook(
            channels.slack_webhook_url, _slack_payload(title, severity, summary, asset_value)
        )
    if channels.webhook_url:
        results["webhook"] = send_webhook(
            channels.webhook_url,
            {
                "event": "finding.created",
                "title": title,
                "severity": severity,
                "summary": summary,
                "recommendation": recommendation,
                "asset_value": asset_value,
            },
        )
    if channels.github_repo and channels.github_token:
        results["github"] = create_github_issue(
            channels.github_repo,
            channels.github_token,
            github_issue_payload(title, severity, summary, recommendation, asset_value),
        )
    if channels.jira_base_url and channels.jira_token and channels.jira_project_key:
        results["jira"] = create_jira_issue(
            channels.jira_base_url,
            channels.jira_email or "",
            channels.jira_token,
            jira_issue_payload(
                channels.jira_project_key, title, severity, summary, recommendation, asset_value
            ),
        )
    if channels.email_to:
        body = (
            f"Önem: {severity.upper()}\nVarlık: {asset_value}\n\n{summary or ''}"
            + (f"\n\nÖnerilen aksiyon: {recommendation}" if recommendation else "")
        )
        results["email"] = send_email(channels.email_to, f"[Argus] {title}", body)

    return results
