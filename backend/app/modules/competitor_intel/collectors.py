"""Rakip istihbarat kaynak konnektorleri.

Amac: bir musterinin izledigi rakip (domain/sirket) icin halka acik degisiklikleri
takip etmek: fiyat degisimi, yeni urun/ozellik, ise alim sinyali (buyume), ust
yonetim degisikligi. Yasal/halka acik kaynaklara dayanir.

- DemoCompetitorCollector: anahtarsiz DEMO konnektor. Rakipten deterministik olarak
  1-2 degisiklik sinyali uretir. Gercek bir kaynak DEGILDIR.
- WebScrapeCollector: web kazima / fiyat-takip API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

from app.core.config import settings
from app.core_services.osint.base import Collector

_CHANGE_TYPES = ["price_change", "new_product", "hiring_signal", "leadership_change"]
_DEPARTMENTS = ["Muhendislik", "Satis", "Pazarlama", "Operasyon"]
_ROLES = ["CTO", "CFO", "Pazarlama Direktoru", "Genel Mudur"]


class DemoCompetitorCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - rakipten deterministik degisiklik sinyali uretir.

    Gercek bir kaynak DEGILDIR; mimariyi anahtarsiz gosterebilmek icindir.
    """

    name = "demo-competitor-watch"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        count = 1 + (seed % 2)  # 1-2 sinyal
        records: list[dict] = []
        for i in range(count):
            change_type = _CHANGE_TYPES[(seed >> i) % len(_CHANGE_TYPES)]
            rec: dict = {
                "source": self.name,
                "asset_type": asset_type,
                "asset_value": asset_value,
                "competitor": asset_value,
                "change_type": change_type,
            }
            if change_type == "price_change":
                direction = "dusurdu" if (seed >> i) & 1 else "artirdi"
                rec["direction"] = direction
                rec["percent"] = 5 + (seed >> (i + 1)) % 40
            elif change_type == "new_product":
                rec["product"] = f"Yeni urun/surum v{1 + (seed >> i) % 5}"
            elif change_type == "hiring_signal":
                rec["department"] = _DEPARTMENTS[(seed >> (i + 1)) % len(_DEPARTMENTS)]
                rec["open_roles"] = 3 + (seed >> (i + 2)) % 20
            else:  # leadership_change
                rec["role"] = _ROLES[(seed >> (i + 1)) % len(_ROLES)]
            records.append(rec)
        return records


class WebScrapeCollector(Collector):
    """Web kazima / fiyat-takip API'si (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    Gercek entegrasyon icin settings'e SCRAPE_API_KEY ekleyin ve asagiyi doldurun.
    """

    name = "web-scrape"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "scrape_api_key", "")
        if not api_key:
            return []
        # Gercek cagri burada yapilir (httpx ile). Anahtarsiz demoda devre disi.
        return []


def get_collectors() -> list[Collector]:
    return [DemoCompetitorCollector(), WebScrapeCollector()]
