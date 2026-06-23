"""Yasadisi site analizoru - yasadisi site sistem promptu + agirlikli sezgisel triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun yasadisi site tespiti analistisin. "
    "Gorevin: bir musterinin markasini/anahtar kelimesini taklit eden ya da istismar eden "
    "supheli bir web sitesini degerlendirmek. Kategoriler: kumar/bahis sitesi, "
    "dolandiricilik/sahte odeme-giris sitesi, marka taklidi. Turkiye'de kumar ve "
    "dolandiricilik BTK'ya (Bilgi Teknolojileri ve Iletisim Kurumu) ihbar edilebilir. "
    "Sana toplanan kanit sinyalleri verilebilir: alan adi kayit yasi (domain_age_days; "
    "kucuk deger = yeni kayit = yuksek risk), site iceriginde gecen kumar/dolandiricilik "
    "anahtar kelimeleri (keyword_hits), sahte odeme/giris formu (has_payment_form), DNS/SSL "
    "durumu. Bu kanitlari degerlendirmene kat. Her bulgu icin: kisa baslik, severity "
    "(info/low/medium/high/critical), Turkce 2-3 cumlelik ozet ve Turkce onerilen aksiyon "
    "(gerekirse BTK ihbar adimini ve toplanan kaniti belirt) uret. Kumar/bahis taklidi "
    "severity en az 'high', sahte odeme/giris en az 'high' olmalidir; guclu kanit varsa 'critical'."
)


def _evidence(raw: dict) -> tuple[int, list[str]]:
    """Toplanan sinyallerden bir risk skoru ve insan-okur kanit satirlari uretir."""
    score = 0
    lines: list[str] = []
    if raw.get("registered") or raw.get("reachable"):
        score += 1
    if raw.get("ssl_observed"):
        score += 1
        lines.append("SSL sertifikasi gozlemlendi (Certificate Transparency)")
    age = raw.get("domain_age_days")
    if isinstance(age, int):
        lines.append(f"alan adi yasi: {age} gun")
        if age < 90:
            score += 2  # yeni kayitli domain'ler kumar/dolandiricilikta tipiktir
    hits = raw.get("keyword_hits") or []
    if hits:
        score += 2
        lines.append("supheli icerik anahtar kelimeleri: " + ", ".join(hits[:6]))
    if raw.get("has_payment_form"):
        score += 2
        lines.append("sahte odeme/giris formu tespit edildi")
    if raw.get("has_mx"):
        score += 1
        lines.append("e-posta (MX) kaydi mevcut")
    if raw.get("search_url"):
        lines.append(f"arama sonucu: {raw['search_url']}")
    return score, lines


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan agirlikli sezgisel siniflandirma (demo/test icin).

    Kategori (kumar/dolandiricilik) en az 'high' uretir; toplanan kanit guclu ise 'critical'a
    yukseltir. Kanit yoksa onceki davranisla (high) geriye-uyumludur.
    """
    domain = raw.get("candidate_domain", "?")
    category = raw.get("category_hint", "fraud")
    score, evidence = _evidence(raw)
    severity = "critical" if score >= 5 else "high"
    evidence_txt = (" Kanit: " + "; ".join(evidence) + ".") if evidence else ""

    if category == "gambling":
        return TriageResult(
            title=f"Kumar/bahis taklit sitesi: {domain}",
            severity=severity,
            summary=(
                f"'{asset_value}' adini kullanan supheli bir kumar/bahis sitesi tespit edildi: "
                f"{domain}. Marka itibarini istismar ediyor ve kullanicilari yaniltabilir."
                + evidence_txt
            ),
            recommendation=(
                "Alan adini ve barindirma saglayicisini dogrulayin, kanit (ekran goruntusu) "
                "toplayin ve BTK Ihbarweb uzerinden ihbar edin; gerekirse erisim engeli talep edin."
            ),
        )
    return TriageResult(
        title=f"Sahte/dolandiricilik sitesi: {domain}",
        severity=severity,
        summary=(
            f"'{asset_value}' markasini taklit eden, sahte odeme/giris amacli olabilecek bir site "
            f"tespit edildi: {domain}. Kullanici bilgileri calinabilir (phishing)." + evidence_txt
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
