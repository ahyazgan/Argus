"""Dark web bulgu analizoru - dark web sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun kidemli dark web tehdit analistisin. "
    "Gorevin: bir musterinin KENDI varligi (domain, e-posta, anahtar kelime) icin "
    "halka acik/yasal kaynaklardan gelen ham bir sizinti bulgusunu degerlendirmek. "
    "Yalnizca savunma amacli calisirsin. Her bulgu icin: kisa baslik, "
    "severity (info/low/medium/high/critical), Turkce 2-3 cumlelik ozet ve "
    "Turkce somut onerilen aksiyon uret. Parola/credential sizintisi varsa severity en az 'high'."
)


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel triyaj (demo/test icin)."""
    has_password = bool(raw.get("password") or raw.get("password_hash"))
    source = raw.get("source", "bilinmeyen kaynak")
    if has_password:
        return TriageResult(
            title=f"{asset_value} icin parola sizintisi tespit edildi",
            severity="high",
            summary=(
                f"'{asset_value}' varligina ait kimlik bilgileri (parola dahil) {source} "
                "kaynaginda acikta bulundu. Hesaplar yetkisiz erisime acik olabilir."
            ),
            recommendation=(
                "Etkilenen hesaplarin parolalarini hemen sifirlatin, MFA zorunlu kilin ve "
                "ayni parolanin kullanildigi diger servisleri kontrol edin."
            ),
        )
    return TriageResult(
        title=f"{asset_value} ile iliskili veri sizintisi",
        severity="medium",
        summary=(
            f"'{asset_value}' varligi {source} kaynaginda bir veri kumesi icinde gecti. "
            "Parola gorunmuyor ancak e-posta/kullanici bilgileri ifsa olmus olabilir."
        ),
        recommendation=(
            "Sizintinin kapsamini dogrulayin, etkilenen kullanicilari bilgilendirin ve "
            "oltalama (phishing) girisimlerine karsi uyanik olun."
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
