"""Marka koruma analizoru - marka koruma sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun marka koruma analistisin. "
    "Gorevin: bir musterinin markasini/alan adini taklit eden benzer (lookalike/typosquat) bir "
    "alan adini degerlendirmek. Teknikler: typosquat (harf hatasi), TLD takasi, homoglyph "
    "(benzer karakter), combosquat (marka+kelime). Riski, alan adinin kayitli olup olmamasina "
    "ve mail (MX) kaydina gore degerlendir. Her bulgu icin: kisa baslik, "
    "severity (info/low/medium/high/critical), Turkce 2-3 cumlelik ozet ve Turkce somut aksiyon "
    "(UDRP/registrar sikayeti, takedown, savunma amacli kayit) uret. Kayitli VE mail kaydi olan "
    "taklit alan adi (aktif oltalama/phishing kapasitesi) severity en az 'high' olmalidir."
)

_TECHNIQUE_TR = {
    "typosquat": "harf hatasi (typosquat)",
    "tld_swap": "uzanti (TLD) takasi",
    "homoglyph": "benzer karakter (homoglyph)",
    "combosquat": "marka + kelime birlesimi (combosquat)",
}


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel triyaj (demo/test icin)."""
    variant = raw.get("variant_domain", "?")
    brand = raw.get("brand", asset_value)
    technique = raw.get("technique", "typosquat")
    technique_tr = _TECHNIQUE_TR.get(technique, technique)
    registered = bool(raw.get("registered"))
    has_mx = bool(raw.get("has_mx"))

    if registered and has_mx:
        return TriageResult(
            title=f"Aktif taklit alan adi: {variant}",
            severity="high",
            summary=(
                f"'{brand}' markasini taklit eden {variant} alan adi {technique_tr} teknigiyle "
                "olusturulmus, kayitli ve mail (MX) kaydina sahip. Bu, aktif oltalama (phishing) "
                "ve sahte e-posta gonderimi icin kullanilabilecegini gosterir."
            ),
            recommendation=(
                "Alan adini ve barindiriciyi dogrulayin, kanit toplayin ve registrar/barindirici "
                "uzerinden takedown ile UDRP/marka sikayeti baslatin; musterileri uyarin."
            ),
        )
    if registered:
        return TriageResult(
            title=f"Kayitli taklit alan adi: {variant}",
            severity="medium",
            summary=(
                f"'{brand}' markasina benzeyen {variant} alan adi {technique_tr} teknigiyle "
                "olusturulmus ve kayitli. Mail kaydi gorunmuyor ancak ileride sahte site/oltalama "
                "icin kullanilabilir."
            ),
            recommendation=(
                "Alan adini izlemeye alin, icerik yayina girerse takedown surecini baslatin ve "
                "gerekirse UDRP/marka sikayeti degerlendirin."
            ),
        )
    return TriageResult(
        title=f"Bos benzer alan adi: {variant}",
        severity="low",
        summary=(
            f"'{brand}' markasina benzeyen {variant} alan adi {technique_tr} teknigiyle uretildi ve "
            "henuz kayitli gorunmuyor. Ucuncu sahislerce kotuye kullanim riski tasir."
        ),
        recommendation=(
            "Bu varyanti savunma amacli kaydetmeyi (defensive registration) degerlendirin ve "
            "yeni kayit feed'inde izlemeye alin."
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
