"""Marka koruma kaynak konnektorleri.

Amac: bir musterinin markasini/alan adini taklit eden benzer (lookalike/typosquat)
alan adlarini ve olasi marka istismarini tespit etmek. Savunma amaclidir: musterinin
KENDI markasi icin halka acik sinyaller uretir, saldiri ICERMEZ.

- LookalikeDomainCollector: anahtarsiz DEMO konnektor. Markadan deterministik olarak
  benzer alan adi adaylari uretir (typosquat, TLD takasi, homoglyph, combosquat).
  Gercek bir kaynak DEGILDIR.
- DomainFeedCollector: yeni kayitli domain feed / WHOIS API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.core_services.osint.base import Collector


def dns_has_answer(payload: dict) -> bool:
    """Google DoH 'resolve' yanitinda cozumlenmis kayit (Answer) var mi (saf, test edilebilir).

    NXDOMAIN / bos yanit -> False; en az bir Answer -> True.
    """
    return bool(payload.get("Answer"))


def _doh_query(name: str, rtype: str) -> bool:
    """Google DNS-over-HTTPS ile bir kaydin (A/MX) var olup olmadigini sorgular.

    Anahtarsiz gercek DNS dogrulamasi. Hata/zaman asiminda False doner (akisi bozmaz).
    """
    try:
        resp = httpx.get(
            "https://dns.google/resolve",
            params={"name": name, "type": rtype},
            timeout=8.0,
        )
        return dns_has_answer(resp.json())
    except (httpx.HTTPError, ValueError):
        return False

# Taklit teknikleri ve uretim icin yardimci havuzlar
_TECHNIQUES = ["typosquat", "tld_swap", "homoglyph", "combosquat"]
_ALT_TLDS = [".net", ".org", ".co", ".xyz", ".online", ".shop"]
_COMBO_WORDS = ["login", "secure", "destek", "hesap", "odeme"]
# Homoglyph / typo karakter takaslari (deterministik secim icin)
_HOMOGLYPH = {"o": "0", "i": "1", "l": "1", "e": "3", "a": "@"}


def _base_name(asset_value: str) -> tuple[str, str]:
    """Marka/alan adindan (etiket, tld) ayristirir. TLD yoksa .com varsayilir."""
    value = asset_value.lower().strip()
    if "." in value:
        label, _, tld = value.partition(".")
        return label.replace(" ", ""), "." + tld
    return value.replace(" ", ""), ".com"


class LookalikeDomainCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - markadan deterministik benzer alan adlari uretir.

    Gercek bir kaynak DEGILDIR; mimariyi anahtarsiz gosterebilmek icindir.
    """

    name = "demo-lookalike-finder"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        label, tld = _base_name(asset_value)
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        count = 1 + (seed % 3)  # 1-3 aday
        records: list[dict] = []
        for i in range(count):
            technique = _TECHNIQUES[(seed >> i) % len(_TECHNIQUES)]
            if technique == "tld_swap":
                variant = label + _ALT_TLDS[(seed >> (i + 1)) % len(_ALT_TLDS)]
            elif technique == "combosquat":
                word = _COMBO_WORDS[(seed >> (i + 1)) % len(_COMBO_WORDS)]
                variant = f"{label}-{word}{tld}"
            elif technique == "homoglyph":
                variant = _apply_homoglyph(label, seed >> (i + 1)) + tld
            else:  # typosquat - bir harf tekrari/dusurme
                variant = _apply_typo(label, seed >> (i + 1)) + tld
            # Kayitli mi / mail (MX) kaydi var mi:
            # - brand_dns_check aciksa GERCEK DNS-over-HTTPS sorgusu
            # - kapaliysa deterministik demo sinyali (test/offline icin)
            if getattr(settings, "brand_dns_check", False):
                registered = _doh_query(variant, "A")
                has_mx = registered and _doh_query(variant, "MX")
            else:
                registered = (seed >> (i + 2)) & 1 == 1
                has_mx = registered and ((seed >> (i + 3)) & 1 == 1)
            records.append(
                {
                    "source": self.name,
                    "asset_type": asset_type,
                    "asset_value": asset_value,
                    "brand": label,
                    "variant_domain": variant,
                    "technique": technique,
                    "registered": registered,
                    "has_mx": has_mx,
                }
            )
        return records


def _apply_homoglyph(label: str, salt: int) -> str:
    for idx, ch in enumerate(label):
        if ch in _HOMOGLYPH and (salt >> idx) & 1:
            return label[:idx] + _HOMOGLYPH[ch] + label[idx + 1 :]
    # Hicbir harf eslesmediyse ilk harfi cift yap (yine de benzer kalir)
    return (label[0] + label) if label else label


def _apply_typo(label: str, salt: int) -> str:
    if len(label) < 2:
        return label + label
    pos = salt % (len(label) - 1)
    # Bitisik iki harfi yer degistir (transposition typo)
    return label[:pos] + label[pos + 1] + label[pos] + label[pos + 2 :]


class DomainFeedCollector(Collector):
    """Yeni kayitli domain feed / WHOIS API'si (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    Gercek entegrasyon icin settings'e BRAND_FEED_API_KEY ekleyin ve asagiyi doldurun.
    """

    name = "domain-feed"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "brand_feed_api_key", "")
        if not api_key:
            return []
        # Gercek cagri burada yapilir (httpx ile). Anahtarsiz demoda devre disi.
        return []


def get_collectors() -> list[Collector]:
    return [LookalikeDomainCollector(), DomainFeedCollector()]
