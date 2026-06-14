"""Sosyal medya hesap taklidi analizoru - sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun sosyal medya marka koruma analistisin. "
    "Gorevin: bir musterinin markasini taklit eden sahte/taklit sosyal medya hesabini "
    "degerlendirmek. Taklit tipleri: handle_squat (benzer kullanici adi), fake_official "
    "(sahte 'resmi' hesap), fake_support (sahte musteri destegi - kimlik avi vektoru). "
    "Riski; dogrulanmis (verified) rozet, takipci sayisi, marka logosu kullanimi ve "
    "biyografide marka adi gecmesine gore degerlendir. Her bulgu icin kisa baslik, severity "
    "(info/low/medium/high/critical), Turkce 2-3 cumlelik ozet ve Turkce somut aksiyon "
    "(platforma taklit/impersonation sikayeti, takedown, kullanicilari uyarma) uret. "
    "Dogrulanmis rozetli sahte hesap 'critical'; sahte musteri destegi en az 'high' olmalidir."
)

_PLATFORM_TR = {"x": "X (Twitter)", "instagram": "Instagram", "facebook": "Facebook",
                "telegram": "Telegram", "tiktok": "TikTok"}
_IMP_TR = {
    "handle_squat": "benzer kullanici adi (handle squatting)",
    "fake_official": "sahte 'resmi' hesap",
    "fake_support": "sahte musteri destegi",
}


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel triyaj (demo/test icin)."""
    platform = _PLATFORM_TR.get(raw.get("platform", ""), raw.get("platform", "sosyal medya"))
    handle = raw.get("handle", "?")
    followers = int(raw.get("followers", 0) or 0)
    verified = bool(raw.get("verified"))
    uses_logo = bool(raw.get("uses_logo"))
    imp_type = raw.get("impersonation_type", "handle_squat")
    imp_tr = _IMP_TR.get(imp_type, imp_type)

    # Severity: dogrulanmis sahte > sahte destek > genis erisimli sahte resmi > ...
    if verified:
        severity = "critical"
    elif imp_type == "fake_support":
        severity = "high"
    elif imp_type == "fake_official" and (uses_logo or followers >= 1000):
        severity = "high"
    elif uses_logo or followers >= 500:
        severity = "medium"
    else:
        severity = "low"

    signals = []
    if verified:
        signals.append("dogrulanmis (verified) rozet")
    if uses_logo:
        signals.append("marka logosu kullanimi")
    if followers:
        signals.append(f"{followers:,} takipci".replace(",", "."))
    signal_txt = ", ".join(signals) if signals else "dusuk gorunurluk"

    title = f"Taklit hesap ({platform}): @{handle}"
    summary = (
        f"'{asset_value}' markasini taklit eden @{handle} hesabi {platform} uzerinde "
        f"{imp_tr} kalibiyla tespit edildi. Sinyaller: {signal_txt}. "
        + (
            "Dogrulanmis rozet bu hesabin guvenilir gorunerek kullanicilari yaniltma riskini "
            "ciddi sekilde artirir."
            if verified
            else "Bu hesap kullanicilari yaniltmak veya kimlik avi icin kullanilabilir."
        )
    )
    recommendation = (
        f"{platform} uzerinden taklit/impersonation sikayeti ve takedown talebi acin; "
        "kanit (ekran goruntusu, profil baglantisi) toplayin"
        + (
            " ve sahte destek hesabinin kullanicilardan bilgi/odeme istemesine karsi musterileri "
            "resmi kanallardan uyarin."
            if imp_type == "fake_support"
            else " ve gerekirse resmi hesabinizi dogrulatip kullanicilari bilgilendirin."
        )
    )
    return TriageResult(title=title, severity=severity, summary=summary, recommendation=recommendation)


def analyze(result: ScanResult, asset_type: str) -> TriageResult:
    return triage(
        result.raw_data,
        result.asset_value,
        asset_type,
        system_prompt=SYSTEM_PROMPT,
        heuristic=heuristic,
    )
