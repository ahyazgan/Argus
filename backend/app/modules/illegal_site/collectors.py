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
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.core_services.osint.base import Collector

# Arama sonucu basligi/linkinde kumar/bahis isaretleri (aksi halde dolandiricilik varsayilir)
_GAMBLING_HINTS = ("bahis", "casino", "bet", "slot", "iddaa", "rulet", "poker")


def parse_cse(payload: dict, asset_value: str) -> list[dict]:
    """Google CSE 'items' yanitini supheli site kayitlarina cevirir (saf)."""
    records: list[dict] = []
    for item in payload.get("items") or []:
        link = item.get("link") or ""
        title = (item.get("title") or "").lower()
        host = urlparse(link).netloc or link
        gambling = any(h in title or h in link.lower() for h in _GAMBLING_HINTS)
        records.append(
            {
                "source": "google-cse",
                "asset_type": "keyword",
                "asset_value": asset_value,
                "candidate_domain": host,
                "url": link,
                "pattern": "search",
                "category_hint": "gambling" if gambling else "fraud",
            }
        )
    return records

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


class GoogleCSECollector(Collector):
    """Google Programmable Search (CSE) ile gercek arama (SEARCH_API_KEY + GOOGLE_CSE_ID).

    Marka/anahtar kelimeyi arar; sonuc alan adlarini supheli site adayi olarak uretir.
    Anahtar yoksa veya hata olursa bos doner (demo konnektore dusulur).
    """

    name = "google-cse"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "search_api_key", "")
        cse_id = getattr(settings, "google_cse_id", "")
        if not api_key or not cse_id:
            return []
        try:
            resp = httpx.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": api_key, "cx": cse_id, "q": f"{asset_value} bahis OR giris OR guncel"},
                timeout=15.0,
            )
            resp.raise_for_status()
            return parse_cse(resp.json(), asset_value)
        except (httpx.HTTPError, ValueError):
            return []


def get_collectors() -> list[Collector]:
    return [SuspiciousSiteCollector(), GoogleCSECollector()]
