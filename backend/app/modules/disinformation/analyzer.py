"""Dezenformasyon analizoru - dezenformasyon sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun dezenformasyon / etki operasyonu analistisin. "
    "Gorevin: bir musterinin markasi/anahtar kelimesi etrafindaki bir manipulasyon sinyalini "
    "degerlendirmek. Sinyal tipleri: koordineli bot agi, sahte haber/yanlis anlati, taklit "
    "(impersonation) hesap, manipule edilmis medya (deepfake). Her bulgu icin: kisa baslik, "
    "severity (info/low/medium/high/critical), Turkce 2-3 cumlelik ozet ve Turkce somut aksiyon "
    "(platforma raporlama, kamuoyu duzeltmesi, hukuki adim) uret. Koordineli bot kampanyasi ve "
    "manipule edilmis medya (deepfake) en az 'high' olmalidir."
)


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel triyaj (demo/test icin)."""
    signal_type = raw.get("signal_type", "fake_news")
    subject = raw.get("subject", asset_value)
    platform = raw.get("platform", "sosyal medya")

    if signal_type == "coordinated_bots":
        count = raw.get("account_count", 0)
        timeframe = raw.get("timeframe", "kisa surede")
        return TriageResult(
            title=f"Koordineli bot kampanyasi: {subject} ({platform})",
            severity="high",
            summary=(
                f"'{subject}' hakkinda {platform} uzerinde {timeframe} icinde ~{count} hesabin "
                "es zamanli/benzer icerik paylastigi koordineli bir bot kampanyasi tespit edildi. "
                "Bu, organik gorunumlu bir manipulasyon/etki operasyonu olabilir."
            ),
            recommendation=(
                "Hesaplari ve icerik kaliplarini delil olarak kaydedin, platforma koordineli "
                "sahte davranis olarak raporlayin ve gerekiyorsa kamuoyu bilgilendirmesi yapin."
            ),
        )

    if signal_type == "manipulated_media":
        media_type = raw.get("media_type", "manipule medya")
        return TriageResult(
            title=f"Manipule edilmis medya (deepfake): {subject}",
            severity="high",
            summary=(
                f"'{subject}' ile iliskili {media_type} {platform} uzerinde dolasiyor. "
                "Manipule medya itibar zedeleme ve yaniltma amacli kullanilabilir."
            ),
            recommendation=(
                "Icerigin kaynagini ve degistirildigini dogrulayin (forensic), platforma kaldirma "
                "(takedown) talebi gonderin ve resmi bir duzeltme yayinlayin."
            ),
        )

    if signal_type == "impersonation_account":
        handle = raw.get("handle", "sahte hesap")
        return TriageResult(
            title=f"Taklit hesap: {handle} ({platform})",
            severity="medium",
            summary=(
                f"'{subject}' adina hareket eden taklit bir hesap ({handle}) {platform} uzerinde "
                "tespit edildi. Kullanicilari yaniltabilir veya dolandiricilik icin kullanilabilir."
            ),
            recommendation=(
                "Hesabi platforma taklit (impersonation) olarak raporlayin, takipcileri uyarin ve "
                "resmi hesaplarinizi dogrulanmis (verified) hale getirin."
            ),
        )

    # fake_news (varsayilan)
    claim = raw.get("claim", "yaniltici iddia")
    return TriageResult(
        title=f"Sahte haber / yanlis anlati: {subject} ({platform})",
        severity="medium",
        summary=(
            f"'{subject}' hakkinda {platform} uzerinde dogrulanmamis bir {claim} yayiliyor. "
            "Yanlis anlati marka itibarini ve kamuoyu algisini olumsuz etkileyebilir."
        ),
        recommendation=(
            "Iddianin kaynagini ve yayilimini izleyin, dogrulanmis bilgiyle hizli bir duzeltme "
            "yayinlayin ve gerekiyorsa platforma yaniltici icerik olarak raporlayin."
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
