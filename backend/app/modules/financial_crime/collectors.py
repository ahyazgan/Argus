"""Finansal suc tespiti kaynak konnektorleri.

Amac: bir musterinin izledigi varlik (kripto cuzdani, sirket, anahtar kelime) icin
finansal suc sinyallerini tespit etmek: kripto ponzi/yuksek getiri vaadi, mixer/
karistirici kullanimi, yaptirimli (sanctioned) tarafla etkilesim, paravan sirket.
Savunma/uyum (compliance) amaclidir; halka acik sinyaller uretir.

- DemoFinancialSignalCollector: anahtarsiz DEMO konnektor. Varliktan deterministik
  finansal suc sinyalleri uretir. Gercek bir kaynak DEGILDIR.
- ChainAnalysisCollector: zincir analizi / yaptirim listesi API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

from app.core.config import settings
from app.core_services.osint.base import Collector

# Varlik tipine gore olasi sinyaller (deterministik secim icin havuz)
_SIGNALS_BY_ASSET: dict[str, list[str]] = {
    "wallet": ["mixer_usage", "sanctioned_counterparty"],
    "company": ["shell_company", "sanctioned_counterparty"],
    "keyword": ["ponzi_scheme"],
}
_DEFAULT_SIGNALS = ["ponzi_scheme", "shell_company"]


class DemoFinancialSignalCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - varliktan deterministik finansal suc sinyali uretir.

    Gercek bir kaynak DEGILDIR; mimariyi anahtarsiz gosterebilmek icindir.
    """

    name = "demo-financial-signals"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        pool = _SIGNALS_BY_ASSET.get(asset_type, _DEFAULT_SIGNALS)
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        count = 1 + (seed % 2)  # 1-2 sinyal
        records: list[dict] = []
        for i in range(count):
            signal_type = pool[(seed >> i) % len(pool)]
            rec: dict = {
                "source": self.name,
                "asset_type": asset_type,
                "asset_value": asset_value,
                "entity": asset_value,
                "signal_type": signal_type,
            }
            if signal_type == "ponzi_scheme":
                rec["promised_return"] = f"%{30 + (seed >> i) % 70} aylik getiri"
            elif signal_type == "mixer_usage":
                rec["mixer"] = ["Tornado", "Wasabi", "ChipMixer"][(seed >> i) % 3]
            elif signal_type == "sanctioned_counterparty":
                rec["list"] = ["OFAC SDN", "EU", "BM"][(seed >> i) % 3]
            elif signal_type == "shell_company":
                rec["indicator"] = "ayni adreste cok sayida sirket / faaliyet izi yok"
            records.append(rec)
        return records


class ChainAnalysisCollector(Collector):
    """Zincir analizi / yaptirim listesi API'si (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    Gercek entegrasyon icin settings'e CHAIN_ANALYSIS_API_KEY ekleyin ve asagiyi doldurun.
    """

    name = "chain-analysis"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "chain_analysis_api_key", "")
        if not api_key:
            return []
        # Gercek cagri burada yapilir (httpx ile). Anahtarsiz demoda devre disi.
        return []


def get_collectors() -> list[Collector]:
    return [DemoFinancialSignalCollector(), ChainAnalysisCollector()]
