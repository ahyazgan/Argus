"""Yasadisi site analizoru - yasadisi site sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun yasadisi site tespiti analistisin. "
    "Gorevin: bir musterinin markasini/anahtar kelimesini taklit eden ya da istismar eden "
    "supheli bir web sitesini degerlendirmek. Kategoriler: kumar/bahis sitesi, "
    "dolandiricilik/sahte odeme-giris sitesi, marka taklidi. Turkiye'de kumar ve "
    "dolandiricilik BTK'ya (Bilgi Teknolojileri ve Iletisim Kurumu) ihbar edilebilir. "
    "Her bulgu icin: kisa baslik, severity (info/low/medium/high/critical), Turkce 2-3 "
    "cumlelik ozet ve Turkce onerilen aksiyon (gerekirse BTK ihbar adimini belirt) uret. "
    "Kumar/bahis taklidi severity en az 'high', sahte odeme/giris en az 'high' olmalidir."
)


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel siniflandirma (demo/test icin)."""
    domain = raw.get("candidate_domain", "?")
    category = raw.get("category_hint", "fraud")
    if category == "gambling":
        return TriageResult(
            title=f"Kumar/bahis taklit sitesi: {domain}",
            severity="high",
            summary=(
                f"'{asset_value}' adini kullanan supheli bir kumar/bahis sitesi tespit edildi: "
                f"{domain}. Marka itibarini istismar ediyor ve kullanicilari yaniltabilir."
            ),
            recommendation=(
                "Alan adini ve barindirma saglayicisini dogrulayin, kanit (ekran goruntusu) "
                "toplayin ve BTK Ihbarweb uzerinden ihbar edin; gerekirse erisim engeli talep edin."
            ),
        )
    return TriageResult(
        title=f"Sahte/dolandiricilik sitesi: {domain}",
        severity="high",
        summary=(
            f"'{asset_value}' markasini taklit eden, sahte odeme/giris amacli olabilecek bir site "
            f"tespit edildi: {domain}. Kullanici bilgileri calinabilir (phishing)."
        ),
        recommendation=(
            "Siteyi dogrulayin, musterileri uyarin, alan adi/SSL kayitlarini inceleyin ve "
            "BTK Ihbarweb ile savciliga/marka avukatina ihbar/sikayet surecini baslatin."
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
