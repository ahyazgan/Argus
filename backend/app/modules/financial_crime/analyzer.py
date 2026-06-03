"""Finansal suc analizoru - finansal suc sistem promptu + heuristic ile triyaj."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult, triage
from app.modules.base import ScanResult

SYSTEM_PROMPT = (
    "Sen Argus Intelligence platformunun finansal suc / uyum (compliance) analistisin. "
    "Gorevin: bir musterinin izledigi varlik (kripto cuzdani, sirket, anahtar kelime) icin "
    "ham bir finansal suc sinyalini degerlendirmek. Sinyal tipleri: ponzi/yuksek getiri vaadi, "
    "mixer/karistirici kullanimi, yaptirimli (sanctioned) tarafla etkilesim, paravan sirket. "
    "Turkiye'de supheli finansal islemler MASAK'a (Mali Suclari Arastirma Kurulu) bildirilebilir. "
    "Her bulgu icin: kisa baslik, severity (info/low/medium/high/critical), Turkce 2-3 cumlelik "
    "ozet ve Turkce somut aksiyon (gerekirse MASAK bildirimi) uret. Yaptirimli tarafla etkilesim "
    "'critical'; mixer kullanimi ve ponzi en az 'high' olmalidir."
)


def heuristic(raw: dict, asset_value: str, asset_type: str) -> TriageResult:
    """API anahtari olmadan calisan sezgisel triyaj (demo/test icin)."""
    signal_type = raw.get("signal_type", "ponzi_scheme")
    entity = raw.get("entity", asset_value)

    if signal_type == "sanctioned_counterparty":
        sanction = raw.get("list", "yaptirim listesi")
        return TriageResult(
            title=f"Yaptirimli tarafla etkilesim: {entity}",
            severity="critical",
            summary=(
                f"'{entity}' varligi {sanction} yaptirim listesindeki bir tarafla iliskili gorunuyor. "
                "Yaptirimli taraflarla islem ciddi yasal ve uyum (compliance) riski tasir."
            ),
            recommendation=(
                "Iliskiyi derhal dondurun, islem gecmisini koruyun, hukuk/uyum birimini bilgilendirin "
                "ve gerekiyorsa MASAK'a supheli islem bildirimi yapin."
            ),
        )

    if signal_type == "mixer_usage":
        mixer = raw.get("mixer", "bir karistirici")
        return TriageResult(
            title=f"Mixer/karistirici kullanimi: {entity}",
            severity="high",
            summary=(
                f"'{entity}' cuzdani {mixer} gibi bir kripto karistirici (mixer/tumbler) ile etkilesimde "
                "gorunuyor. Bu, fon kaynagini gizleme ve para aklama girisimine isaret edebilir."
            ),
            recommendation=(
                "Cuzdan akisini zincir analiziyle dogrulayin, ilgili hesaplari isaretleyin ve "
                "supheli islem olarak MASAK bildirimini degerlendirin."
            ),
        )

    if signal_type == "shell_company":
        indicator = raw.get("indicator", "paravan sirket gostergeleri")
        return TriageResult(
            title=f"Paravan sirket suphesi: {entity}",
            severity="medium",
            summary=(
                f"'{entity}' icin paravan (shell) sirket gostergeleri tespit edildi: {indicator}. "
                "Gercek faaliyeti olmayan sirketler para aklama/orgun gizlenmesinde kullanilabilir."
            ),
            recommendation=(
                "Ticaret sicili, gercek faydalanici (UBO) ve adres bilgilerini dogrulayin; "
                "supheli ise musteri durum tespiti (KYC/EDD) derinlestirin."
            ),
        )

    # ponzi_scheme (varsayilan)
    promised = raw.get("promised_return", "asiri yuksek getiri")
    return TriageResult(
        title=f"Olasi ponzi/yuksek getiri dolandiriciligi: {entity}",
        severity="high",
        summary=(
            f"'{entity}' ile iliskili, {promised} vaat eden bir yatirim yapisi tespit edildi. "
            "Surdurulemez getiri vaatleri klasik ponzi/piramit dolandiriciligi gostergesidir."
        ),
        recommendation=(
            "Yapinin lisans/izin durumunu (SPK) dogrulayin, magdurlari uyarin ve gerekiyorsa "
            "MASAK/savciliga bildirim/sikayet surecini baslatin."
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
