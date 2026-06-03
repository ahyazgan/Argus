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
from app.modules.security_scan.analyzer import heuristic as security_heuristic
from app.modules.security_scan.collectors import SurfaceProbeCollector
from app.modules.brand_protection.analyzer import heuristic as brand_heuristic
from app.modules.brand_protection.collectors import LookalikeDomainCollector
from app.modules.financial_crime.analyzer import heuristic as financial_heuristic
from app.modules.financial_crime.collectors import DemoFinancialSignalCollector


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
    assert "security_scan" in live  # ucuncu canli modul
    assert "brand_protection" in live  # dorduncu canli modul
    assert "financial_crime" in live  # besinci canli modul
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


def test_security_heuristic_exposed_sensitive_service_is_critical():
    res = security_heuristic(
        {"issue_type": "exposed_service", "service": "PostgreSQL", "port": 5432,
         "sensitive": True, "target": "ornek.com"},
        "ornek.com",
        "domain",
    )
    assert res.severity == "critical"
    assert "PostgreSQL" in res.title


def test_security_heuristic_exposed_admin_panel_is_high():
    res = security_heuristic(
        {"issue_type": "exposed_admin_panel", "path": "/admin", "target": "ornek.com"},
        "ornek.com",
        "domain",
    )
    assert res.severity == "high"


def test_security_heuristic_missing_header_is_low():
    res = security_heuristic(
        {"issue_type": "missing_security_header", "header": "Content-Security-Policy",
         "target": "ornek.com"},
        "ornek.com",
        "domain",
    )
    assert res.severity == "low"
    assert "Content-Security-Policy" in res.title


def test_surface_probe_collector_is_deterministic():
    c = SurfaceProbeCollector()
    recs = c.collect("domain", "ornek.com")
    assert len(recs) >= 1
    assert all("issue_type" in r for r in recs)
    assert c.collect("domain", "ornek.com") == recs  # deterministik


def test_brand_heuristic_registered_with_mx_is_high():
    res = brand_heuristic(
        {"variant_domain": "markam-login.com", "brand": "markam", "technique": "combosquat",
         "registered": True, "has_mx": True},
        "markam.com",
        "brand",
    )
    assert res.severity == "high"
    assert "markam-login.com" in res.title


def test_brand_heuristic_registered_no_mx_is_medium():
    res = brand_heuristic(
        {"variant_domain": "markam.net", "brand": "markam", "technique": "tld_swap",
         "registered": True, "has_mx": False},
        "markam.com",
        "brand",
    )
    assert res.severity == "medium"


def test_brand_heuristic_unregistered_is_low():
    res = brand_heuristic(
        {"variant_domain": "markma.com", "brand": "markam", "technique": "typosquat",
         "registered": False, "has_mx": False},
        "markam.com",
        "brand",
    )
    assert res.severity == "low"


def test_lookalike_collector_is_deterministic():
    c = LookalikeDomainCollector()
    recs = c.collect("brand", "markam")
    assert len(recs) >= 1
    assert all("variant_domain" in r and "technique" in r for r in recs)
    assert c.collect("brand", "markam") == recs  # deterministik


def test_financial_heuristic_sanctioned_is_critical():
    res = financial_heuristic(
        {"signal_type": "sanctioned_counterparty", "list": "OFAC SDN", "entity": "0xabc"},
        "0xabc",
        "wallet",
    )
    assert res.severity == "critical"
    assert "MASAK" in res.recommendation


def test_financial_heuristic_mixer_is_high():
    res = financial_heuristic(
        {"signal_type": "mixer_usage", "mixer": "Tornado", "entity": "0xabc"},
        "0xabc",
        "wallet",
    )
    assert res.severity == "high"


def test_financial_heuristic_shell_company_is_medium():
    res = financial_heuristic(
        {"signal_type": "shell_company", "entity": "ACME Ltd"},
        "ACME Ltd",
        "company",
    )
    assert res.severity == "medium"


def test_financial_signal_collector_is_deterministic():
    c = DemoFinancialSignalCollector()
    recs = c.collect("wallet", "0xabc")
    assert len(recs) >= 1
    assert all("signal_type" in r for r in recs)
    assert c.collect("wallet", "0xabc") == recs  # deterministik
