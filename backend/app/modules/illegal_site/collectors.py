"""Yasadisi site tespiti kaynak konnektorleri.

Amac: bir markayi/anahtar kelimeyi taklit eden ya da istismar eden supheli siteleri
(kumar/bahis, dolandiricilik, sahte odeme/giris) tespit etmek; gerektiginde BTK'ya
ihbar icin kanit toplamak.

- SuspiciousSiteCollector: anahtarsiz DEMO konnektor. Izlenen marka/kelimeden, supheli
  kalip ve TLD'lerle deterministik aday alan adlari uretir (gercek bir kaynak DEGILDIR).
- LookalikeSiteCollector: anahtarsiz GERCEK konnektor. Markadan typosquat/combosquat
  adaylari uretir, bunlari Certificate Transparency (crt.sh) + DNS-over-HTTPS ile dogrular.
  `illegal_dns_check` bayragiyla acilir (kapaliyken bos doner; demo akisini bozmaz).
- SearchEngineCollector: Google Programmable Search API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.core_services.osint.base import Collector
from app.modules.illegal_site.enrichment import _doh_query, crt_sh_domains

# Supheli kaliplar (kumar/bahis ve dolandiricilik/sahte giris)
_GAMBLING = ["bahis", "casino", "bet", "slot", "giris", "guncel"]
_FRAUD = ["odeme", "dogrulama", "destek", "hesap", "kampanya"]
_TLDS = [".com", ".net", ".xyz", ".online", ".click", ".vip"]
# Kumar/bahis siteleri sik sik bu TLD'lerde toplanir (combosquat uretimi icin).
_RISKY_TLDS = [".xyz", ".online", ".click", ".vip", ".bet", ".live"]


def _base_label(asset_value: str) -> str:
    """Marka/alan adindan alan etiketini (TLD'siz) ayristirir."""
    return asset_value.lower().strip().replace(" ", "").partition(".")[0]


def _category_for(word: str) -> str:
    """Bir combosquat kelimesinin hangi kategoriye isaret ettigini belirler."""
    return "gambling" if word in _GAMBLING else "fraud"


def lookalike_variants(asset_value: str) -> list[dict]:
    """Markadan deterministik combosquat aday alan adlari uretir (SAF - ag yok).

    Her aday icin (candidate_domain, pattern, category_hint, technique) doner. DNS/CT
    dogrulamasi yapmaz; bunu cagiran konnektor (LookalikeSiteCollector) yapar.
    """
    label = _base_label(asset_value)
    variants: list[dict] = []
    seen: set[str] = set()
    if len(label) < 3:
        return variants
    for word in (*_GAMBLING, *_FRAUD):
        tld = _RISKY_TLDS[(len(word) + len(label)) % len(_RISKY_TLDS)]
        for candidate in (f"{label}-{word}{tld}", f"{label}{word}{tld}"):
            if candidate not in seen:
                seen.add(candidate)
                variants.append(
                    {
                        "candidate_domain": candidate,
                        "pattern": word,
                        "category_hint": _category_for(word),
                        "technique": "combosquat",
                    }
                )
    return variants


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


class LookalikeSiteCollector(Collector):
    """Anahtarsiz GERCEK konnektor - typosquat/combosquat adaylarini CT + DNS ile dogrular.

    Iki gercek, ucretsiz kaynak kullanir:
      1. Certificate Transparency loglari (crt.sh) - markayi iceren, SSL sertifikali domain'ler.
      2. Markadan turetilen combosquat adaylarinin DNS-over-HTTPS ile canli (A kaydi) dogrulamasi.
    Yalnizca GERCEKTEN kayitli/cozumlenen adaylari dondurur (gurultu yerine kanit).
    `illegal_dns_check` kapaliyken bos doner (demo akisini SuspiciousSiteCollector tasir).
    """

    name = "lookalike-dns"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        if not getattr(settings, "illegal_dns_check", False):
            return []
        label = _base_label(asset_value)
        records: list[dict] = []
        emitted: set[str] = set()

        # 1) Certificate Transparency loglari (crt.sh) - dogrudan kanit.
        for domain in crt_sh_domains(label):
            if domain in emitted:
                continue
            emitted.add(domain)
            records.append(
                {
                    "source": f"{self.name}:crt.sh",
                    "asset_type": asset_type,
                    "asset_value": asset_value,
                    "candidate_domain": domain,
                    "category_hint": "fraud",
                    "technique": "cert_transparency",
                    "registered": True,
                    "ssl_observed": True,
                }
            )

        # 2) Combosquat adaylari - yalnizca DNS'te canli olanlari al.
        for variant in lookalike_variants(asset_value):
            domain = variant["candidate_domain"]
            if domain in emitted or not _doh_query(domain, "A"):
                continue
            emitted.add(domain)
            records.append(
                {
                    "source": f"{self.name}:doh",
                    "asset_type": asset_type,
                    "asset_value": asset_value,
                    **variant,
                    "registered": True,
                    "has_mx": _doh_query(domain, "MX"),
                }
            )
        return records


class SearchEngineCollector(Collector):
    """Google Programmable Search (Custom Search JSON API) tabanli gercek konnektor.

    `search_api_key` + `search_engine_id` (CSE "cx") yapilandirilmissa marka + kumar/
    dolandiricilik terimleriyle dork sorgusu calistirir ve sonuc alan adlarini aday yapar.
    Anahtar yoksa bos liste doner (demo akisini bozmaz).
    """

    name = "search-engine"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "search_api_key", "")
        cx = getattr(settings, "search_engine_id", "")
        if not api_key or not cx:
            return []
        label = _base_label(asset_value)
        query = f'"{label}" (bahis OR casino OR slot OR giris OR odeme OR dogrulama)'
        try:
            resp = httpx.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": api_key, "cx": cx, "q": query, "num": 10},
                timeout=15.0,
            )
            resp.raise_for_status()
            items = resp.json().get("items", []) or []
        except (httpx.HTTPError, ValueError):
            return []

        records: list[dict] = []
        seen: set[str] = set()
        for item in items:
            domain = str(item.get("displayLink", "")).lower().lstrip("www.")
            if not domain or domain in seen or label not in domain:
                continue
            seen.add(domain)
            snippet = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
            gambling = any(k in snippet for k in ("bahis", "casino", "slot", "bet"))
            records.append(
                {
                    "source": f"{self.name}",
                    "asset_type": asset_type,
                    "asset_value": asset_value,
                    "candidate_domain": domain,
                    "category_hint": "gambling" if gambling else "fraud",
                    "technique": "search_result",
                    "search_title": item.get("title", ""),
                    "search_url": item.get("link", ""),
                }
            )
        return records


def get_collectors() -> list[Collector]:
    """Aktif konnektor listesi. Demo her zaman acik; gercekler bayrak/anahtar varsa is gorur."""
    return [SuspiciousSiteCollector(), LookalikeSiteCollector(), SearchEngineCollector()]
