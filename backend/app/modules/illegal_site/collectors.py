"""Yasadisi site tespiti kaynak konnektorleri.

Amac: bir markayi/anahtar kelimeyi taklit eden ya da istismar eden supheli siteleri
(kumar/bahis, dolandiricilik, sahte odeme/giris) tespit etmek; gerektiginde BTK'ya
ihbar icin kanit toplamak.

- SuspiciousSiteCollector: anahtarsiz DEMO konnektor. Izlenen marka/kelimeden, supheli
  kalip ve TLD'lerle deterministik aday alan adlari uretir (gercek bir kaynak DEGILDIR).
- SearchEngineCollector: arama motoru / domain feed API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

from app.core.config import settings
from app.core_services.osint.base import Collector

# Supheli kaliplar (kumar/bahis ve dolandiricilik/sahte giris)
_GAMBLING = ["bahis", "casino", "bet", "slot", "giris", "guncel"]
_FRAUD = ["odeme", "dogrulama", "destek", "hesap", "kampanya"]
_TLDS = [".com", ".net", ".xyz", ".online", ".click", ".vip"]


class SuspiciousSiteCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - deterministik supheli aday alan adlari uretir."""

    name = "demo-domain-scanner"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        base = asset_value.lower().replace(" ", "").replace(".", "")
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        count = 1 + (seed % 3)  # 1-3 aday
        records: list[dict] = []
        for i in range(count):
            gambling = (seed >> i) & 1 == 1
            pool = _GAMBLING if gambling else _FRAUD
            word = pool[(seed >> (i + 1)) % len(pool)]
            tld = _TLDS[(seed >> (i + 2)) % len(_TLDS)]
            candidate = f"{base}-{word}{tld}"
            records.append(
                {
                    "source": f"{self.name}",
                    "asset_type": asset_type,
                    "asset_value": asset_value,
                    "candidate_domain": candidate,
                    "pattern": word,
                    "category_hint": "gambling" if gambling else "fraud",
                }
            )
        return records


class SearchEngineCollector(Collector):
    """Arama motoru / domain-feed tabanli gercek konnektor (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    Gercek entegrasyon icin settings'e bir arama API anahtari ekleyin.
    """

    name = "search-engine"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "search_api_key", "")
        if not api_key:
            return []
        # Gercek cagri burada yapilir (httpx ile). Anahtarsiz demoda devre disi.
        return []


def get_collectors() -> list[Collector]:
    return [SuspiciousSiteCollector(), SearchEngineCollector()]
