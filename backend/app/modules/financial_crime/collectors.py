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

import httpx

from app.core.config import settings
from app.core_services.osint.base import Collector


def parse_opensanctions(payload: dict, entity: str, threshold: float = 0.7) -> list[dict]:
    """OpenSanctions /match yanitini yaptirim sinyallerine cevirir (saf).

    Esik (score) ustundeki eslesmeler 'sanctioned_counterparty' kaydi uretir.
    """
    records: list[dict] = []
    responses = payload.get("responses") or {}
    for _qid, block in responses.items():
        for res in block.get("results") or []:
            score = res.get("score") or 0
            if score < threshold:
                continue
            datasets = res.get("datasets") or []
            records.append(
                {
                    "source": "opensanctions",
                    "asset_type": "company",
                    "asset_value": entity,
                    "entity": res.get("caption", entity),
                    "signal_type": "sanctioned_counterparty",
                    "list": ", ".join(datasets[:3]) or "OpenSanctions",
                    "score": round(float(score), 2),
                }
            )
    return records

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


class OpenSanctionsCollector(Collector):
    """OpenSanctions yaptirim/PEP eslestirme (CHAIN_ANALYSIS_API_KEY = ApiKey).

    Sirket/anahtar kelime/cuzdan adini yaptirim listelerine karsi sorgular. Anahtarsiz
    veya hata durumunda bos doner (demo konnektore dusulur).
    """

    name = "opensanctions"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "chain_analysis_api_key", "")
        if not api_key:
            return []
        schema = "Company" if asset_type == "company" else "Thing"
        try:
            resp = httpx.post(
                "https://api.opensanctions.org/match/default",
                headers={"Authorization": f"ApiKey {api_key}"},
                json={"queries": {"q1": {"schema": schema, "properties": {"name": [asset_value]}}}},
                timeout=15.0,
            )
            resp.raise_for_status()
            return parse_opensanctions(resp.json(), asset_value)
        except (httpx.HTTPError, ValueError):
            return []


def get_collectors() -> list[Collector]:
    return [DemoFinancialSignalCollector(), OpenSanctionsCollector()]
