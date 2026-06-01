"""PDF rapor uretimi - WeasyPrint ile Turkce bulgu raporu (cikti katmani)."""
from __future__ import annotations

from datetime import datetime

from jinja2 import Template

_SEVERITY_TR = {
    "critical": ("KRITIK", "#b91c1c"),
    "high": ("YUKSEK", "#c2410c"),
    "medium": ("ORTA", "#a16207"),
    "low": ("DUSUK", "#1d4ed8"),
    "info": ("BILGI", "#475569"),
}

_TEMPLATE = Template(
    """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<style>
  @page { size: A4; margin: 2cm; }
  body { font-family: 'DejaVu Sans', sans-serif; color: #1e293b; font-size: 11px; }
  h1 { color: #0f172a; font-size: 22px; margin-bottom: 2px; }
  .sub { color: #64748b; font-size: 12px; margin-bottom: 16px; }
  .meta { background:#f1f5f9; padding:10px 14px; border-radius:6px; margin-bottom:18px; }
  .finding { border:1px solid #e2e8f0; border-radius:8px; padding:12px 14px; margin-bottom:12px; page-break-inside: avoid; }
  .badge { display:inline-block; color:#fff; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:bold; }
  .ftitle { font-size:13px; font-weight:bold; margin:6px 0; }
  .label { color:#64748b; font-size:10px; text-transform:uppercase; letter-spacing:.04em; }
  .rec { background:#f8fafc; border-left:3px solid #0ea5e9; padding:6px 10px; margin-top:6px; }
  .empty { color:#64748b; font-style:italic; }
</style>
</head>
<body>
  <h1>Argus Intelligence — Tehdit Istihbarati Raporu</h1>
  <div class="sub">Bulgu ozeti</div>
  <div class="meta">
    <strong>Kurum:</strong> {{ org_name }}<br>
    <strong>Olusturma:</strong> {{ generated_at }}<br>
    <strong>Toplam bulgu:</strong> {{ findings|length }}
  </div>

  {% if findings|length == 0 %}
    <p class="empty">Bu kapsamda bulgu tespit edilmedi.</p>
  {% endif %}

  {% for f in findings %}
  <div class="finding">
    <span class="badge" style="background:{{ f.color }}">{{ f.severity_label }}</span>
    <span class="label">&nbsp;{{ f.source }} • {{ f.detected_at }}</span>
    <div class="ftitle">{{ f.title }}</div>
    <div><span class="label">Varlik:</span> {{ f.asset_value }}</div>
    {% if f.summary %}<p>{{ f.summary }}</p>{% endif %}
    {% if f.recommendation %}<div class="rec"><span class="label">Onerilen aksiyon:</span><br>{{ f.recommendation }}</div>{% endif %}
  </div>
  {% endfor %}
</body>
</html>
"""
)


def render_findings_pdf(org_name: str, findings: list) -> bytes:
    """Finding ORM nesneleri listesinden Turkce PDF rapor uretir (bytes)."""
    from weasyprint import HTML  # gec import (agir bagimlilik)

    rows = []
    for f in findings:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        label, color = _SEVERITY_TR.get(sev, (sev.upper(), "#475569"))
        rows.append(
            {
                "title": f.title,
                "severity_label": label,
                "color": color,
                "source": f.source,
                "asset_value": f.asset_value,
                "summary": f.summary,
                "recommendation": f.recommendation,
                "detected_at": f.detected_at.strftime("%d.%m.%Y %H:%M")
                if getattr(f, "detected_at", None)
                else "",
            }
        )

    html = _TEMPLATE.render(
        org_name=org_name,
        generated_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        findings=rows,
    )
    return HTML(string=html).write_pdf()
