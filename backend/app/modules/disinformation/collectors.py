"""Dezenformasyon tespiti kaynak konnektorleri.

Amac: bir musterinin markasi/anahtar kelimesi etrafindaki manipulasyon ve
dezenformasyonu tespit etmek: koordineli bot agi, sahte haber/yanlis anlati,
taklit (impersonation) hesap, manipule edilmis medya (deepfake). Yasal/halka
acik sosyal sinyallere dayanir.

- DemoNarrativeCollector: anahtarsiz DEMO konnektor. Konudan deterministik olarak
  1-2 dezenformasyon sinyali uretir. Gercek bir kaynak DEGILDIR.
- SocialApiCollector: sosyal medya / anlati izleme API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib
from xml.etree import ElementTree as ET

import httpx

from app.core.config import settings
from app.core_services.osint.base import Collector


def parse_news_rss(xml_text: str, subject: str, limit: int = 5) -> list[dict]:
    """Google News RSS XML'ini medya-mention sinyallerine cevirir (saf).

    Konu hakkindaki haberleri 'fake_news' (incelenecek anlati) adayi olarak uretir.
    """
    records: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    for item in list(root.iterfind(".//item"))[:limit]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = item.findtext("{*}source") or item.findtext("source") or "haber"
        if not title:
            continue
        records.append(
            {
                "source": "google-news",
                "asset_type": "keyword",
                "asset_value": subject,
                "subject": subject,
                "signal_type": "fake_news",
                "platform": str(source),
                "claim": title,
                "url": link,
            }
        )
    return records

_SIGNAL_TYPES = ["coordinated_bots", "fake_news", "impersonation_account", "manipulated_media"]
_PLATFORMS = ["X", "Telegram", "Facebook", "TikTok"]


class DemoNarrativeCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - konudan deterministik dezenformasyon sinyali uretir.

    Gercek bir kaynak DEGILDIR; mimariyi anahtarsiz gosterebilmek icindir.
    """

    name = "demo-narrative-watch"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        count = 1 + (seed % 2)  # 1-2 sinyal
        records: list[dict] = []
        for i in range(count):
            signal_type = _SIGNAL_TYPES[(seed >> i) % len(_SIGNAL_TYPES)]
            platform = _PLATFORMS[(seed >> (i + 1)) % len(_PLATFORMS)]
            rec: dict = {
                "source": self.name,
                "asset_type": asset_type,
                "asset_value": asset_value,
                "subject": asset_value,
                "signal_type": signal_type,
                "platform": platform,
            }
            if signal_type == "coordinated_bots":
                rec["account_count"] = 50 + (seed >> i) % 500
                rec["timeframe"] = "son 24 saat"
            elif signal_type == "fake_news":
                rec["claim"] = "dogrulanmamis/yaniltici iddia"
            elif signal_type == "impersonation_account":
                rec["handle"] = f"@{asset_value.lower().replace(' ', '')}_resmi"
            else:  # manipulated_media
                rec["media_type"] = "deepfake video/gorsel"
            records.append(rec)
        return records


class GoogleNewsCollector(Collector):
    """Google News RSS ile gercek, ANAHTARSIZ medya-mention izleme.

    Konu (marka/anahtar kelime) hakkindaki guncel haberleri getirir; incelenecek anlati
    adaylari uretir. DISINFO_NEWS=false ise atlanir. Hata durumunda bos doner.
    """

    name = "google-news"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        if not getattr(settings, "disinfo_news", False):
            return []
        try:
            resp = httpx.get(
                "https://news.google.com/rss/search",
                params={"q": asset_value, "hl": "tr", "gl": "TR", "ceid": "TR:tr"},
                headers={"user-agent": "Argus-Intelligence"},
                timeout=15.0,
            )
            resp.raise_for_status()
            return parse_news_rss(resp.text, asset_value)
        except httpx.HTTPError:
            return []


def get_collectors() -> list[Collector]:
    return [DemoNarrativeCollector(), GoogleNewsCollector()]
