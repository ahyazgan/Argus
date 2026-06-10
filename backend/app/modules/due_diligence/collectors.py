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

from app.core.config import settings
from app.core_services.osint.base import Collector

_RECORD_TYPES = ["litigation", "enforcement", "bankruptcy", "adverse_media", "tax_debt"]


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


class CourtRecordsCollector(Collector):
    """Mahkeme/sicil/ticaret kaydi API'si (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    Gercek entegrasyon icin settings'e COURT_RECORDS_API_KEY ekleyin ve asagiyi doldurun.
    """

    name = "court-records"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "court_records_api_key", "")
        if not api_key:
            return []
        # Gercek cagri burada yapilir (httpx ile). Anahtarsiz demoda devre disi.
        return []


def get_collectors() -> list[Collector]:
    return [DemoRegistryCollector(), CourtRecordsCollector()]
