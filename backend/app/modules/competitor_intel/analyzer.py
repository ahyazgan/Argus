"""Rakip istihbarat analizoru - rakip istihbarat sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun rakip istihbarat (competitive intelligence) analistisin. "
    "Gorevin: bir musterinin izledigi rakipte halka acik bir degisikligi degerlendirmek. "
    "Degisiklik tipleri: fiyat degisimi, yeni urun/surum, ise alim sinyali (buyume), ust yonetim "
    "degisikligi. Bu bir tehdit degil, is firsati/rekabet sinyalidir; severity'yi ticari ETKIYE "
    "gore ver (genelde info/low/medium). Her bulgu icin: kisa baslik, severity, Turkce 2-3 "
    "cumlelik ozet ve Turkce somut aksiyon (rekabetci yanit onerisi) uret. Agresif fiyat dususu "
    "veya yeni urun lansmani en az 'medium' olmalidir."
)


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel triyaj (demo/test icin)."""
    change_type = raw.get("change_type", "new_product")
    competitor = raw.get("competitor", asset_value)

    if change_type == "price_change":
        direction = raw.get("direction", "degistirdi")
        percent = raw.get("percent", 0)
        # Belirgin fiyat dususu rekabetci baski yaratir -> medium
        severity = "medium" if (direction == "dusurdu" and percent >= 10) else "low"
        return TriageResult(
            title=f"Rakip fiyat degisimi: {competitor} fiyati %{percent} {direction}",
            severity=severity,
            summary=(
                f"'{competitor}' fiyatlarini %{percent} oraninda {direction}. "
                "Bu, pazardaki fiyat konumlandirmasini ve musteri tercihini etkileyebilir."
            ),
            recommendation=(
                "Kendi fiyat/kampanya stratejinizi gozden gecirin, etkilenen segmentleri analiz edin "
                "ve gerekiyorsa rekabetci bir yanit kurgulayin."
            ),
        )

    if change_type == "new_product":
        product = raw.get("product", "yeni bir urun")
        return TriageResult(
            title=f"Rakip yeni urun/surum: {competitor}",
            severity="medium",
            summary=(
                f"'{competitor}' {product} lansmani yapti gorunuyor. Yeni ozellikler pazardaki "
                "beklentileri yukseltebilir ve rekabet dengesini degistirebilir."
            ),
            recommendation=(
                "Urunun ozelliklerini ve fiyatini analiz edin, kendi yol haritanizla kiyaslayin ve "
                "farklilastirici mesajinizi guncelleyin."
            ),
        )

    if change_type == "hiring_signal":
        department = raw.get("department", "bir birim")
        open_roles = raw.get("open_roles", 0)
        return TriageResult(
            title=f"Rakip buyume sinyali: {competitor} ({department})",
            severity="low",
            summary=(
                f"'{competitor}' {department} biriminde {open_roles} acik pozisyon ilani veriyor. "
                "Bu, ilgili alanda yatirim/buyume planina isaret edebilir."
            ),
            recommendation=(
                "Hangi alanda buyudugunu degerlendirin (urun, satis, pazar), yetenek rekabetini ve "
                "olasi stratejik yonelimi takip edin."
            ),
        )

    # leadership_change (varsayilan)
    role = raw.get("role", "ust yonetim")
    return TriageResult(
        title=f"Rakip yonetim degisikligi: {competitor} ({role})",
        severity="low",
        summary=(
            f"'{competitor}' sirketinde {role} pozisyonunda bir degisiklik gozlemlendi. "
            "Ust yonetim degisiklikleri strateji ve onceliklerde kaymaya isaret edebilir."
        ),
        recommendation=(
            "Yeni yoneticinin gecmisini ve olasi stratejik etkisini degerlendirin; "
            "rakibin yon degisikligine karsi senaryolarinizi guncelleyin."
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
