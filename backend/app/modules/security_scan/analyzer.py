"""Guvenlik tarama analizoru - guvenlik sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun savunma amacli guvenlik analistisin. "
    "Gorevin: bir musterinin KENDI varligi (domain/ip/url) icin pasif gozlemden gelen ham bir "
    "guvenlik sinyalini degerlendirmek. Saldiri/exploit onermezsin; yalnizca riski aciklar ve "
    "duzeltme (remediation) onerirsin. Bulgu tipleri: eksik guvenlik basligi, zayif TLS surumu, "
    "acikta kalan yonetim paneli, acikta kalan servis/port. Her bulgu icin: kisa baslik, "
    "severity (info/low/medium/high/critical), Turkce 2-3 cumlelik ozet ve Turkce somut duzeltme "
    "onerisi uret. Hassas bir servisin (veritabani, RDP) internete aciklanmasi 'critical', "
    "acikta kalan yonetim paneli en az 'high' olmalidir."
)

# Bulgu tipi basina sezgisel siniflandirma (anahtar yoksa kullanilir)
_HEADER_RISK = {
    "Strict-Transport-Security": "HTTPS zorlanmadigi icin SSL-stripping/oltalama riski artar.",
    "Content-Security-Policy": "XSS ve veri sizdirma saldirilarina karsi koruma zayiflar.",
    "X-Frame-Options": "Clickjacking saldirilarina acik hale gelir.",
}


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel triyaj (demo/test icin)."""
    issue_type = raw.get("issue_type", "missing_security_header")
    target = raw.get("target", asset_value)

    if issue_type == "exposed_service":
        service = raw.get("service", "bilinmeyen servis")
        port = raw.get("port", "?")
        sensitive = bool(raw.get("sensitive"))
        severity = "critical" if sensitive else "high"
        return TriageResult(
            title=f"Acikta kalan servis: {service} ({target}:{port})",
            severity=severity,
            summary=(
                f"'{target}' uzerinde {service} servisi {port} portundan internete acik gorunuyor. "
                + (
                    "Hassas bir servisin dis dunyaya aciklanmasi yetkisiz erisim ve veri sizintisi riski tasir."
                    if sensitive
                    else "Beklenmeyen bir yonetim arayuzu/servis dis dunyaya aciklanmis olabilir."
                )
            ),
            recommendation=(
                f"{service} ({port}) erisimini guvenlik duvari/VPN ile kisitlayin, gerekmiyorsa kapatin, "
                "kimlik dogrulama ve guncel yamalari dogrulayin."
            ),
        )

    if issue_type == "exposed_admin_panel":
        path = raw.get("path", "/admin")
        return TriageResult(
            title=f"Acikta kalan yonetim paneli: {target}{path}",
            severity="high",
            summary=(
                f"'{target}{path}' yolu disaridan erisilebilir gorunuyor. Yonetim arayuzlerinin "
                "internete acik olmasi kaba kuvvet (brute force) ve yetkisiz erisim riski yaratir."
            ),
            recommendation=(
                "Paneli IP allowlist/VPN arkasina alin, guclu kimlik dogrulama ve MFA zorunlu kilin, "
                "varsayilan kullanici adlarini degistirin."
            ),
        )

    if issue_type == "weak_tls":
        protocol = raw.get("protocol", "TLS 1.0")
        return TriageResult(
            title=f"Zayif TLS surumu: {protocol} ({target})",
            severity="medium",
            summary=(
                f"'{target}' eski/zayif {protocol} protokolunu destekliyor. Bu surumler bilinen "
                "zafiyetler icerir ve sifreli trafigin kirilma riskini artirir."
            ),
            recommendation=(
                "Sunucu yapilandirmasinda TLS 1.2/1.3 disindaki surumleri devre disi birakin ve "
                "guclu sifre paketlerine (cipher suite) gecin."
            ),
        )

    # missing_security_header (varsayilan)
    header = raw.get("header", "Strict-Transport-Security")
    detail = _HEADER_RISK.get(header, "Tarayici tabanli saldirilara karsi koruma zayiflar.")
    return TriageResult(
        title=f"Eksik guvenlik basligi: {header} ({target})",
        severity="low",
        summary=(
            f"'{target}' HTTP yanitlarinda {header} guvenlik basligi bulunmuyor. {detail}"
        ),
        recommendation=(
            f"Web sunucusu/uygulama yapilandirmasina {header} basligini ekleyin ve diger temel "
            "guvenlik basliklarini da etkinlestirin."
        ),
    )


def analyze(result: ScanResult, asset_type: str) -> TriageResult:
    return triage(
        result.raw_data,
        result.asset_value,
        asset_type,
        system_prompt=SYSTEM_PROMPT,
        heuristic=heuristic,
    )
