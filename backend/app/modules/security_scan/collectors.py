"""Guvenlik tarama kaynak konnektorleri.

Amac: bir musterinin KENDI varligi (domain/ip/url) icin pasif, savunma amacli bir
guvenlik yuzeyi (attack surface) degerlendirmesi yapmak: eksik guvenlik basliklari,
zayif TLS, acikta kalan yonetim paneli, beklenmeyen acik servis/port. Saldiri/exploit
ICERMEZ; yalnizca halka acik gozlemlere dayanan sinyaller uretir.

- SurfaceProbeCollector: anahtarsiz DEMO konnektor. Varliktan deterministik olarak 1-3
  guvenlik bulgusu adayi uretir (gercek bir tarayici DEGILDIR).
- ShodanCollector: Shodan tarzi pasif yuzey API'si (anahtar varsa). Anahtarsiz bos doner.

Yeni gercek kaynaklar buraya birer Collector olarak eklenir; modul mantigi degismez.
"""
from __future__ import annotations

import hashlib

from app.core.config import settings
from app.core_services.osint.base import Collector

# Olasi bulgu tipleri ve tasidiklari ek alanlar (deterministik demo icin havuz)
_HEADERS = ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options"]
_TLS = ["TLS 1.0", "TLS 1.1", "SSLv3"]
_ADMIN_PATHS = ["/admin", "/wp-admin", "/phpmyadmin", "/.git/"]
# (servis adi, port, hassas mi) - hassas servisler kritik kabul edilir
_SERVICES = [
    ("PostgreSQL", 5432, True),
    ("Redis", 6379, True),
    ("RDP", 3389, True),
    ("Elasticsearch", 9200, True),
    ("HTTP yonetim arayuzu", 8080, False),
]
_ISSUE_TYPES = ["missing_security_header", "weak_tls", "exposed_admin_panel", "exposed_service"]


class SurfaceProbeCollector(Collector):
    """Anahtar gerektirmeyen demo konnektor - varliktan deterministik guvenlik bulgulari uretir.

    Gercek bir tarayici DEGILDIR; mimariyi anahtarsiz gosterebilmek icindir.
    """

    name = "demo-surface-probe"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        seed = int(hashlib.sha256(asset_value.encode()).hexdigest(), 16)
        count = 1 + (seed % 3)  # 1-3 bulgu
        records: list[dict] = []
        for i in range(count):
            issue_type = _ISSUE_TYPES[(seed >> i) % len(_ISSUE_TYPES)]
            rec: dict = {
                "source": self.name,
                "asset_type": asset_type,
                "asset_value": asset_value,
                "target": asset_value,
                "issue_type": issue_type,
            }
            if issue_type == "missing_security_header":
                rec["header"] = _HEADERS[(seed >> (i + 1)) % len(_HEADERS)]
            elif issue_type == "weak_tls":
                rec["protocol"] = _TLS[(seed >> (i + 1)) % len(_TLS)]
            elif issue_type == "exposed_admin_panel":
                rec["path"] = _ADMIN_PATHS[(seed >> (i + 1)) % len(_ADMIN_PATHS)]
            else:  # exposed_service
                svc, port, sensitive = _SERVICES[(seed >> (i + 1)) % len(_SERVICES)]
                rec["service"] = svc
                rec["port"] = port
                rec["sensitive"] = sensitive
            records.append(rec)
        return records


class ShodanCollector(Collector):
    """Shodan tarzi pasif yuzey/port API'si (anahtar varsa).

    Anahtar yapilandirilmamissa bos liste doner (demo akisini bozmaz).
    Gercek entegrasyon icin settings'e SHODAN_API_KEY ekleyin ve asagiyi doldurun.
    """

    name = "shodan"

    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        api_key = getattr(settings, "shodan_api_key", "")
        if not api_key:
            return []
        # Gercek cagri burada yapilir (httpx ile). Anahtarsiz demoda devre disi.
        return []


def get_collectors() -> list[Collector]:
    return [SurfaceProbeCollector(), ShodanCollector()]
