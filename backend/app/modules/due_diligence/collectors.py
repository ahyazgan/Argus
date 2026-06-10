"""Due diligence kaynak konnektorleri.

Amac: bir sirket hakkinda risk degerlendirmesi icin halka acik olumsuz kayitlari
toplamak: dava/mahkeme, icra takibi, iflas/konkordato, olumsuz medya, vergi/borc.
Ortaklik, satin alma veya tedarikci onceki risk taramasi (KYC/EDD) icindir.

- DemoRegistryCollector: anahtarsiz DEMO konnektor. Sirketten deterministik olarak
  1-2 olumsuz kayit uretir. Gercek bir kaynak DEGILDIR.
- CourtRecordsCollector: mahkeme/sicil/ticaret kaydi API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.core_services.osint.base import Collector

_RECORD_TYPES = ["litigation", "enforcement", "bankruptcy", "adverse_media", "tax_debt"]

# OpenCorporates'ta risk gostergesi sayilan (aktif olmayan) durum anahtar kelimeleri
_INACTIVE_MARKERS = ("dissolved", "inactive", "liquidation", "closed", "struck", "cancelled")


def parse_opencorporates(payload: dict, company: str) -> list[dict]:
    """OpenCorporates 'companies/search' yanitini due-diligence kayitlarina cevirir (saf).

    Yalnizca risk gostergesi olan (aktif olmayan / tasfiye) sirketleri kayit olarak uretir.
    """
    records: list[dict] = []
    results = (payload.get("results") or {}).get("companies") or []
    for item in results:
        c = item.get("company") or {}
        status = (c.get("current_status") or "").strip()
        inactive = c.get("inactive") is True or any(m in status.lower() for m in _INACTIVE_MARKERS)
        if not inactive:
            continue
        records.append(
            {
                "source": "opencorporates",
                "asset_type": "company",
                "asset_value": company,
                "company": c.get("name", company),
                "record_type": "bankruptcy",
                "status": status or "aktif degil",
                "jurisdiction": c.get("jurisdiction_code"),
            }
        )
    return records


class DemoRegistryCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - sirketten deterministik olumsuz kayit uretir.

    Gercek bir kaynak DEGILDIR; mimariyi anahtarsiz gosterebilmek icindir.
    """

    name = "demo-registry-check"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        count = 1 + (seed % 2)  # 1-2 kayit
        records: list[dict] = []
        for i in range(count):
            record_type = _RECORD_TYPES[(seed >> i) % len(_RECORD_TYPES)]
            rec: dict = {
                "source": self.name,
                "asset_type": asset_type,
                "asset_value": asset_value,
                "company": asset_value,
                "record_type": record_type,
            }
            if record_type == "litigation":
                rec["case_no"] = f"2024/{1000 + (seed >> i) % 9000}"
                rec["role"] = "davali" if (seed >> i) & 1 else "davaci"
            elif record_type == "enforcement":
                rec["amount"] = f"{(1 + (seed >> i) % 50) * 10000} TL"
            elif record_type == "bankruptcy":
                rec["status"] = "konkordato" if (seed >> i) & 1 else "iflas erteleme"
            elif record_type == "adverse_media":
                rec["topic"] = ["yolsuzluk iddiasi", "ceza sorusturmasi", "isci hakki ihlali"][
                    (seed >> i) % 3
                ]
            else:  # tax_debt
                rec["amount"] = f"{(1 + (seed >> i) % 100) * 5000} TL"
            records.append(rec)
        return records


class OpenCorporatesCollector(Collector):
    """OpenCorporates sirket sicili (COURT_RECORDS_API_KEY = api_token).

    Aktif olmayan / tasfiye halindeki sirketleri risk kaydi olarak uretir. Anahtarsiz
    veya hata durumunda bos doner (demo konnektore dusulur).
    """

    name = "opencorporates"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        token = getattr(settings, "court_records_api_key", "")
        if not token or asset_type != "company":
            return []
        try:
            resp = httpx.get(
                "https://api.opencorporates.com/v0.4/companies/search",
                params={"q": asset_value, "api_token": token, "per_page": 10},
                timeout=15.0,
            )
            resp.raise_for_status()
            return parse_opencorporates(resp.json(), asset_value)
        except (httpx.HTTPError, ValueError):
            return []


def get_collectors() -> list[Collector]:
    return [DemoRegistryCollector(), OpenCorporatesCollector()]
