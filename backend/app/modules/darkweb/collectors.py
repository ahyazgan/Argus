"""Dark web izleme kaynak konnektorleri.

ONEMLI (yasal/etik): Bu modul SAVUNMA amaclidir. Yalnizca musterinin KENDI varligina
(domain/e-posta/anahtar kelime) ait, halka acik veya yasal API'lerden gelen sizinti
verisini sorgular. Yasadisi pazar yeri tarayicisi / Tor crawler ICERMEZ.

- HIBPCollector: HaveIBeenPwned tarzi ucretli API (anahtar varsa). Anahtar yoksa atlanir.
- DemoLeakCollector: Anahtarsiz, deterministik ornek veri uretir. Sunum/test bagimsiz olsun diye.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

from app.core.config import settings
from app.core_services.osint.base import Collector


class DemoLeakCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - varlik degerinden deterministik ornek uretir.

    Gercek bir kaynak DEGILDIR; mimariyi anahtarsiz gosterebilmek icindir.
    """

    name = "demo-leak-feed"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        # Varliga gore 0-2 arasi deterministik "sizinti" uret
        count = seed % 3
        records: list[dict] = []
        breaches = ["MegaUpload2019", "ForumDump2021", "CloudLeak2023"]
        for i in range(count):
            has_pw = (seed >> (i + 1)) & 1 == 1
            rec = {
                "source": f"{self.name}:{breaches[(seed >> i) % len(breaches)]}",
                "asset_type": asset_type,
                "asset_value": asset_value,
                "leaked_field": "email" if asset_type == "email" else "domain_mention",
                "breach_name": breaches[(seed >> i) % len(breaches)],
            }
            if has_pw:
                rec["password_hash"] = hashlib.md5(f"{asset_value}{i}".encode()).hexdigest()
                rec["password"] = "*** (hash mevcut)"
            records.append(rec)
        return records


class HIBPCollector(Collector):
    """HaveIBeenPwned tarzi ucretli sizinti API'si (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    Gercek entegrasyon icin: settings'e HIBP_API_KEY ekleyin ve asagiyi doldurun.
    """

    name = "hibp"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "hibp_api_key", "")
        if not api_key or asset_type != "email":
            return []
        # Gercek cagri burada yapilir (httpx ile). Anahtarsiz demoda devre disi.
        return []


def get_collectors() -> list[Collector]:
    """Aktif konnektor listesi. Demo her zaman acik; gercekler anahtar varsa eklenir."""
    collectors: list[Collector] = [DemoLeakCollector(), HIBPCollector()]
    return collectors
