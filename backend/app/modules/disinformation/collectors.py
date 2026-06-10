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

from app.core.config import settings
from app.core_services.osint.base import Collector

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


class SocialApiCollector(Collector):
    """Sosyal medya / anlati izleme API'si (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    Gercek entegrasyon icin settings'e SOCIAL_API_KEY ekleyin ve asagiyi doldurun.
    """

    name = "social-api"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "social_api_key", "")
        if not api_key:
            return []
        # Gercek cagri burada yapilir (httpx ile). Anahtarsiz demoda devre disi.
        return []


def get_collectors() -> list[Collector]:
    return [DemoNarrativeCollector(), SocialApiCollector()]
