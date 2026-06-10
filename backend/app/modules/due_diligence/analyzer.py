"""Due diligence analizoru - due diligence sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun due diligence (sirket risk) analistisin. "
    "Gorevin: bir sirket hakkinda halka acik olumsuz bir kaydi degerlendirmek. Kayit tipleri: "
    "dava/mahkeme, icra takibi, iflas/konkordato, olumsuz medya, vergi/borc. Amac, ortaklik/"
    "satin alma/tedarikci karari oncesi riski ortaya koymaktir. Her bulgu icin: kisa baslik, "
    "severity (info/low/medium/high/critical), Turkce 2-3 cumlelik ozet ve Turkce somut aksiyon "
    "(dogrulama, ek inceleme, karar onerisi) uret. Iflas/konkordato ve icra takibi en az 'high', "
    "olumsuz medya ve dava en az 'medium' olmalidir."
)


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel triyaj (demo/test icin)."""
    record_type = raw.get("record_type", "litigation")
    company = raw.get("company", asset_value)

    if record_type == "bankruptcy":
        status = raw.get("status", "iflas/konkordato")
        return TriageResult(
            title=f"Mali aciz riski: {company} ({status})",
            severity="high",
            summary=(
                f"'{company}' hakkinda {status} kaydi tespit edildi. Bu, sirketin odeme gucu ve "
                "surekliligi acisindan ciddi bir mali risk gostergesidir."
            ),
            recommendation=(
                f"Guncel mali tablolari ve {status} surecinin durumunu dogrulayin; ticari iliski "
                "veya yatirim kararini bu risk isiginda yeniden degerlendirin."
            ),
        )

    if record_type == "enforcement":
        amount = raw.get("amount", "belirsiz tutar")
        return TriageResult(
            title=f"Icra takibi: {company} ({amount})",
            severity="high",
            summary=(
                f"'{company}' aleyhine {amount} tutarinda icra takibi kaydi bulundu. Aktif icra "
                "takipleri likidite sorunlarina ve odeme guvenilirligi riskine isaret eder."
            ),
            recommendation=(
                "Takibin guncel durumunu ve toplam borc yukunu dogrulayin; odeme kosullarini "
                "(pesin/teminat) buna gore belirleyin."
            ),
        )

    if record_type == "adverse_media":
        topic = raw.get("topic", "olumsuz haber")
        return TriageResult(
            title=f"Olumsuz medya: {company}",
            severity="medium",
            summary=(
                f"'{company}' ile iliskili olumsuz medya tespit edildi (konu: {topic}). Itibar ve "
                "uyum (compliance) riski tasiyabilir."
            ),
            recommendation=(
                "Haberin kaynagini ve dogrulugunu teyit edin, konunun hukuki/duzenleyici bir sonucu "
                "olup olmadigini arastirin ve riski karar dosyasina ekleyin."
            ),
        )

    if record_type == "tax_debt":
        amount = raw.get("amount", "belirsiz tutar")
        return TriageResult(
            title=f"Vergi/borc kaydi: {company} ({amount})",
            severity="medium",
            summary=(
                f"'{company}' icin {amount} tutarinda vergi/borc kaydi gorunuyor. Mali disiplin ve "
                "nakit akisi acisindan dikkat gerektirir."
            ),
            recommendation=(
                "Borcun guncelligini ve yapilandirilip yapilandirilmadigini dogrulayin; mali "
                "saglamligi diger gostergelerle birlikte degerlendirin."
            ),
        )

    # litigation (varsayilan)
    case_no = raw.get("case_no", "?")
    role = raw.get("role", "taraf")
    return TriageResult(
        title=f"Dava kaydi: {company} ({role}, {case_no})",
        severity="medium",
        summary=(
            f"'{company}' bir davada {role} olarak gorunuyor (dosya {case_no}). Davanin konusu ve "
            "tutari sirket icin hukuki/mali risk tasiyabilir."
        ),
        recommendation=(
            "Dosya konusunu, talep tutarini ve safhasini dogrulayin; onemli ise hukuk birimi "
            "gorusu alarak karar dosyasina isleyin."
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
