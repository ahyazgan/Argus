"""Cekirdek birim testleri - DB gerektirmez (saf fonksiyonlar)."""
from __future__ import annotations

from app.core.plans import PLANS, PlanTier, module_limit_for
from app.core.security import hash_password, verify_password
from app.core.utils import slugify
from app.modules.catalog import CATALOG, VALID_MODULE_KEYS
from app.modules.darkweb.analyzer import heuristic as darkweb_heuristic
from app.modules.darkweb.collectors import DemoLeakCollector
from app.modules.illegal_site.analyzer import heuristic as illegal_heuristic
from app.modules.illegal_site.collectors import SuspiciousSiteCollector


def test_slugify_turkish():
    assert slugify("Güvenlik Şirketi") == "guvenlik-sirketi"
    assert slugify("İstanbul A.Ş.") == "istanbul-a-s"
    assert slugify("") == "org"


def test_password_hash_roundtrip():
    h = hash_password("sifre12345")
    assert h != "sifre12345"
    assert verify_password("sifre12345", h)
    assert not verify_password("yanlis", h)


def test_plan_limits():
    assert module_limit_for(PlanTier.STARTER) == 2
    assert module_limit_for(PlanTier.PRO) == 5
    assert module_limit_for(PlanTier.ENTERPRISE) >= len(CATALOG)
    assert set(PLANS.keys()) == set(PlanTier)


def test_catalog_has_live_modules():
    live = {m.key for m in CATALOG if m.enabled}
    assert "darkweb" in live
    assert "illegal_site" in live  # ikinci canli modul
    assert "darkweb" in VALID_MODULE_KEYS
    assert len(CATALOG) == 9  # gorseldeki 9 modul


def test_darkweb_heuristic_password_leak_is_high():
    res = darkweb_heuristic({"password": "x", "source": "test"}, "ornek.com", "domain")
    assert res.severity == "high"
    assert "ornek.com" in res.title


def test_darkweb_heuristic_no_password_is_medium():
    res = darkweb_heuristic({"source": "test"}, "ornek.com", "domain")
    assert res.severity == "medium"


def test_illegal_site_heuristic_gambling_is_high():
    res = illegal_heuristic(
        {"candidate_domain": "markam-bahis.com", "category_hint": "gambling"}, "markam", "brand"
    )
    assert res.severity == "high"
    assert "BTK" in res.recommendation


def test_demo_leak_collector_is_deterministic():
    c = DemoLeakCollector()
    a = c.collect("email", "kullanici@ornek.com")
    b = c.collect("email", "kullanici@ornek.com")
    assert a == b  # ayni varlik -> ayni sonuc (deterministik)


def test_suspicious_site_collector_produces_candidates():
    c = SuspiciousSiteCollector()
    recs = c.collect("brand", "markam")
    assert len(recs) >= 1
    assert all("candidate_domain" in r for r in recs)
    assert c.collect("brand", "markam") == recs  # deterministik
