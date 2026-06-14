"""Rakip istihbarat kaynak konnektorleri.

Amac: bir musterinin izledigi rakip (domain/sirket) icin halka acik degisiklikleri
takip etmek: fiyat degisimi, yeni urun/ozellik, ise alim sinyali (buyume), ust
yonetim degisikligi. Yasal/halka acik kaynaklara dayanir.

- DemoCompetitorCollector: anahtarsiz DEMO konnektor. Rakipten deterministik olarak
  1-2 degisiklik sinyali uretir. Gercek bir kaynak DEGILDIR.
- HomepageWatchCollector: rakip ana sayfasini ANAHTARSIZ ceker; ise alim/lansman
  sinyallerini sezgisel tespit eder (COMPETITOR_WEB_WATCH=true). Genel fiyat/urun
  cikarimi icin bir kazima saglayicisi (SCRAPE_API_KEY) ileride takilabilir.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import settings
from app.core_services.osint.base import Collector

_CHANGE_TYPES = ["price_change", "new_product", "hiring_signal", "leadership_change"]

# Ana sayfa metninde sinyal isaretleri (kucuk harf eslesme)
_HIRING_HINTS = ("kariyer", "careers", "ise alim", "biz e katil", "join us", "acik pozisyon", "we're hiring")
_PRODUCT_HINTS = ("lansman", "yeni urun", "duyuru", "tanitti", "launch", "introducing", "yeni surum", "announc")


def _normalize_url(asset_value: str) -> str:
    """Domain/sirket degerinden taranabilir bir URL uretir."""
    v = asset_value.strip()
    if not v.startswith(("http://", "https://")):
        v = "https://" + v
    return v


def parse_competitor_html(html: str, competitor: str, base_url: str = "") -> list[dict]:
    """Rakip ana sayfasi HTML'inden degisiklik sinyali adaylari uretir (saf, sezgisel).

    - hiring_signal: kariyer/ise alim baglantilari/metni
    - new_product: lansman/duyuru/yeni urun ifadeleri
    Bulunamazsa bos liste doner (gurultuyu sinirlamak icin yalnizca isaret varsa uretir).
    """
    text = (html or "").lower()
    records: list[dict] = []

    def _rec(change_type: str, detail: str, **extra) -> dict:
        return {
            "source": "homepage-watch",
            "asset_type": "domain",
            "asset_value": competitor,
            "competitor": competitor,
            "change_type": change_type,
            "detail": detail,
            **extra,
        }

    if any(h in text for h in _HIRING_HINTS):
        # Kariyer sayfasi baglantisini yakalamaya calis
        m = re.search(r'href=["\']([^"\']*(?:kariyer|career)[^"\']*)["\']', text)
        career_url = urljoin(base_url, m.group(1)) if (m and base_url) else None
        records.append(
            _rec("hiring_signal", "Ana sayfada kariyer/ise alim isareti", department="genel",
                 open_roles=0, **({"career_url": career_url} if career_url else {}))
        )

    if any(h in text for h in _PRODUCT_HINTS):
        records.append(_rec("new_product", "Ana sayfada lansman/duyuru ifadesi", product="duyuru tespit edildi"))

    return records
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


class HomepageWatchCollector(Collector):
    """Rakip ana sayfasini ANAHTARSIZ izleyen gercek konnektor.

    COMPETITOR_WEB_WATCH=true ise rakibin (domain) ana sayfasini ceker ve ise alim /
    lansman sinyallerini sezgisel olarak tespit eder. Bayrak kapaliysa veya hata
    durumunda bos doner (demo konnektore dusulur). Genel fiyat/urun cikarimi icin
    SCRAPE_API_KEY ile bir kazima saglayicisi takilabilir (asagidaki not).
    """

    name = "homepage-watch"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        if not getattr(settings, "competitor_web_watch", False) or asset_type != "domain":
            return []
        url = _normalize_url(asset_value)
        try:
            resp = httpx.get(
                url,
                headers={"user-agent": "Argus-Intelligence"},
                timeout=15.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            base = f"{urlparse(str(resp.url)).scheme}://{urlparse(str(resp.url)).netloc}"
            return parse_competitor_html(resp.text, asset_value, base_url=base)
        except httpx.HTTPError:
            return []


def get_collectors() -> list[Collector]:
    return [DemoCompetitorCollector(), HomepageWatchCollector()]
