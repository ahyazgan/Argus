"""Sosyal medya hesap taklidi kaynak konnektorleri.

Amac: bir musterinin markasini taklit eden sahte/taklit sosyal medya hesaplarini
(handle squatting, sahte 'resmi' hesap, sahte musteri destegi) tespit etmek.
Savunma amaclidir: yalnizca halka acik profil sinyalleri uretir, hesap ele gecirme
veya saldiri ICERMEZ.

- DemoImpersonationCollector: anahtarsiz DEMO konnektor. Markadan deterministik olarak
  platformlar arası taklit hesap adaylari uretir (gercek bir kaynak DEGILDIR).
- SocialSearchCollector: sosyal medya hesap arama API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.core_services.osint.base import Collector

# Izlenen platformlar ve taklit kaliplari (deterministik demo icin havuz)
_PLATFORMS = ["x", "instagram", "facebook", "telegram", "tiktok"]
# Taklit tipleri: handle benzetme, sahte resmi hesap, sahte musteri destegi
_IMP_TYPES = ["handle_squat", "fake_official", "fake_support"]
_SUFFIXES = ["_official", ".tr", "destek", "_support", "_resmi", "app"]


def parse_social_search(payload: dict, asset_value: str) -> list[dict]:
    """Genel sosyal hesap arama API yanitini taklit kayitlarina cevirir (saf, test edilebilir).

    Beklenen sema: {"accounts": [{platform, handle, url, display_name, verified,
    followers, uses_logo, bio}]}. Cikti, social_media analyzer/heuristic ile uyumludur.
    """
    brand = asset_value.lower().strip()
    records: list[dict] = []
    for acc in payload.get("accounts") or []:
        handle = acc.get("handle") or acc.get("username") or ""
        bio = (acc.get("bio") or acc.get("description") or "").lower()
        # Taklit tipini handle/bio'dan sezgisel cikar
        h = handle.lower()
        if any(w in h or w in bio for w in ("destek", "support", "yardim")):
            imp_type = "fake_support"
        elif any(w in h or w in bio for w in ("official", "resmi", "verified")):
            imp_type = "fake_official"
        else:
            imp_type = "handle_squat"
        records.append(
            {
                "source": "social-search",
                "asset_type": "brand",
                "asset_value": asset_value,
                "platform": acc.get("platform", "sosyal medya"),
                "handle": handle,
                "profile_url": acc.get("url"),
                "display_name": acc.get("display_name") or acc.get("name"),
                "verified": bool(acc.get("verified")),
                "followers": int(acc.get("followers") or 0),
                "uses_logo": bool(acc.get("uses_logo")),
                "bio_mentions_brand": brand in bio if brand else False,
                "impersonation_type": imp_type,
            }
        )
    return records


class DemoImpersonationCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - markadan deterministik taklit hesap adaylari uretir.

    Gercek bir kaynak DEGILDIR; mimariyi anahtarsiz gosterebilmek icindir.
    """

    name = "demo-social-impersonation"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        base = asset_value.lower().replace(" ", "").replace("@", "")
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        count = 1 + (seed % 3)  # 1-3 aday
        records: list[dict] = []
        for i in range(count):
            platform = _PLATFORMS[(seed >> i) % len(_PLATFORMS)]
            imp_type = _IMP_TYPES[(seed >> (i + 1)) % len(_IMP_TYPES)]
            suffix = _SUFFIXES[(seed >> (i + 2)) % len(_SUFFIXES)]
            handle = f"{base}{suffix}"
            verified = (seed >> (i + 3)) & 1 == 1 and imp_type == "fake_official"
            uses_logo = (seed >> (i + 4)) & 1 == 1
            followers = (seed >> (i + 2)) % 50000
            records.append(
                {
                    "source": self.name,
                    "asset_type": asset_type,
                    "asset_value": asset_value,
                    "platform": platform,
                    "handle": handle,
                    "profile_url": f"https://{platform}.example/{handle}",
                    "display_name": f"{asset_value} {suffix.strip('_.')}".strip(),
                    "verified": verified,
                    "followers": followers,
                    "uses_logo": uses_logo,
                    "bio_mentions_brand": (seed >> (i + 5)) & 1 == 1,
                    "impersonation_type": imp_type,
                }
            )
        return records


class SocialSearchCollector(Collector):
    """Sosyal medya hesap arama API'si (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    """

    name = "social-search"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "social_search_api_key", "")
        if not api_key:
            return []
        try:
            resp = httpx.get(
                "https://api.socialsearch.example/v1/accounts/search",
                params={"q": asset_value},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15.0,
            )
            resp.raise_for_status()
            return parse_social_search(resp.json(), asset_value)
        except (httpx.HTTPError, ValueError):
            return []  # API hatasi demo/tarama akisini bozmasin


def get_collectors() -> list[Collector]:
    return [DemoImpersonationCollector(), SocialSearchCollector()]
