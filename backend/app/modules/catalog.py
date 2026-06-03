"""Tum modullerin statik katalogu (gorseldeki 9 modul).

Sadece `enabled=True` olanlarin calisan bir uygulamasi vardir ve kayit defterine
eklenir. Digerleri arayuzde "yakinda" olarak gosterilir. Yeni bir modul canliya
alindiginda burada `enabled=True` yapilir ve `modules/<ad>/module.py` eklenir.
"""
from __future__ import annotations

from app.modules.base import ModuleMeta

CATALOG: list[ModuleMeta] = [
    ModuleMeta(
        key="darkweb",
        name="Dark web izleme",
        description="Veri sizintisi, kimlik bilgisi (credential) leak izleme",
        category="dark_web",
        asset_types=["domain", "email", "keyword"],
        enabled=True,
    ),
    ModuleMeta(
        key="security_scan",
        name="Guvenlik tarama",
        description="Web/mobil acik tespiti, pentest yuzeyi, bounty",
        category="security",
        asset_types=["domain", "ip", "url"],
        enabled=True,
    ),
    ModuleMeta(
        key="illegal_site",
        name="Yasadisi site tespiti",
        description="Kumar, dolandiricilik, BTK ihbar",
        category="illegal",
        asset_types=["keyword", "brand"],
        enabled=True,
    ),
    ModuleMeta(
        key="brand_protection",
        name="Marka koruma",
        description="Taklit site, logo korsanligi, domain izleme",
        category="brand",
        asset_types=["domain", "brand"],
        enabled=True,
    ),
    ModuleMeta(
        key="competitor_intel",
        name="Rakip istihbarat",
        description="Fiyat, urun, ise alim takibi",
        category="competitor",
        asset_types=["domain", "company"],
        enabled=False,
    ),
    ModuleMeta(
        key="financial_crime",
        name="Finansal suc tespiti",
        description="Kripto ponzi, para aklama, MASAK",
        category="financial",
        asset_types=["wallet", "company", "keyword"],
        enabled=False,
    ),
    ModuleMeta(
        key="disinformation",
        name="Dezenformasyon tespiti",
        description="Fake haber, bot hesap, manipulasyon",
        category="disinformation",
        asset_types=["brand", "keyword"],
        enabled=False,
    ),
    ModuleMeta(
        key="due_diligence",
        name="Due diligence",
        description="Sirket risk, mahkeme, icra takibi",
        category="due_diligence",
        asset_types=["company"],
        enabled=False,
    ),
    ModuleMeta(
        key="ai_testing",
        name="AI sistem testi",
        description="Prompt injection, model guvenligi",
        category="ai_testing",
        asset_types=["endpoint"],
        enabled=False,
    ),
]

CATALOG_BY_KEY: dict[str, ModuleMeta] = {m.key: m for m in CATALOG}
VALID_MODULE_KEYS: set[str] = set(CATALOG_BY_KEY.keys())
