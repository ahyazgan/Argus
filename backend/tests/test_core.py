"""Cekirdek birim testleri - DB gerektirmez (saf fonksiyonlar)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.plans import PLANS, PlanTier, module_limit_for
from app.core.security import hash_password, verify_password
from app.core.utils import finding_fingerprint, severity_at_least, slugify
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
from app.modules.competitor_intel.analyzer import heuristic as competitor_heuristic
from app.modules.disinformation.analyzer import heuristic as disinfo_heuristic
from app.modules.due_diligence.analyzer import heuristic as dd_heuristic
from app.modules.ai_testing.analyzer import heuristic as ai_heuristic
from app.modules import load_modules
from app.modules.base import all_module_keys
from app.core_services.queue.scheduling import (
    ALLOWED_SCAN_INTERVALS,
    is_due,
    select_due_monitors,
)


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


def test_catalog_all_modules_live():
    # Tum katalog (9 modul) artik canli
    live = {m.key for m in CATALOG if m.enabled}
    assert live == VALID_MODULE_KEYS
    assert len(CATALOG) == 9  # gorseldeki 9 modul


def test_all_modules_register():
    """load_modules() tum katalog modullerini kayit defterine eklemeli."""
    load_modules()
    registered = set(all_module_keys())
    assert registered == VALID_MODULE_KEYS


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


def test_competitor_heuristic_new_product_is_medium():
    res = competitor_heuristic(
        {"change_type": "new_product", "product": "v2", "competitor": "RakipAS"},
        "RakipAS",
        "company",
    )
    assert res.severity == "medium"


def test_competitor_heuristic_price_drop_is_medium():
    res = competitor_heuristic(
        {"change_type": "price_change", "direction": "dusurdu", "percent": 25,
         "competitor": "RakipAS"},
        "RakipAS",
        "company",
    )
    assert res.severity == "medium"


def test_disinfo_heuristic_coordinated_bots_is_high():
    res = disinfo_heuristic(
        {"signal_type": "coordinated_bots", "account_count": 300, "platform": "X",
         "subject": "Markam"},
        "Markam",
        "brand",
    )
    assert res.severity == "high"


def test_disinfo_heuristic_impersonation_is_medium():
    res = disinfo_heuristic(
        {"signal_type": "impersonation_account", "handle": "@markam_resmi", "platform": "X",
         "subject": "Markam"},
        "Markam",
        "brand",
    )
    assert res.severity == "medium"


def test_dd_heuristic_bankruptcy_is_high():
    res = dd_heuristic(
        {"record_type": "bankruptcy", "status": "konkordato", "company": "ACME"},
        "ACME",
        "company",
    )
    assert res.severity == "high"
    assert "konkordato" in res.summary


def test_dd_heuristic_litigation_is_medium():
    res = dd_heuristic(
        {"record_type": "litigation", "case_no": "2024/1234", "role": "davali", "company": "ACME"},
        "ACME",
        "company",
    )
    assert res.severity == "medium"


def test_ai_heuristic_data_leakage_is_critical():
    res = ai_heuristic(
        {"vuln_type": "data_leakage", "endpoint": "https://api.ornek.com/chat"},
        "https://api.ornek.com/chat",
        "endpoint",
    )
    assert res.severity == "critical"


def test_ai_heuristic_prompt_injection_is_high():
    res = ai_heuristic(
        {"vuln_type": "prompt_injection", "endpoint": "https://api.ornek.com/chat"},
        "https://api.ornek.com/chat",
        "endpoint",
    )
    assert res.severity == "high"


def test_ai_heuristic_no_rate_limit_is_low():
    res = ai_heuristic(
        {"vuln_type": "no_rate_limit", "endpoint": "https://api.ornek.com/chat"},
        "https://api.ornek.com/chat",
        "endpoint",
    )
    assert res.severity == "low"


# --- Zamanlanmis tarama (Celery beat dispatcher) saf mantik testleri ---

NOW = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)


@dataclass
class _FakeMonitor:
    is_active: bool = True
    scan_interval_minutes: int | None = None
    last_scanned_at: datetime | None = None


def test_is_due_manual_never_due():
    # interval None => sadece manuel, asla otomatik
    assert is_due(None, None, NOW) is False
    assert is_due(0, None, NOW) is False


def test_is_due_never_scanned_is_due():
    assert is_due(60, None, NOW) is True


def test_is_due_respects_interval():
    # 60 dk aralik; 30 dk once tarandi => henuz degil
    assert is_due(60, NOW - timedelta(minutes=30), NOW) is False
    # tam 60 dk once => vadesi geldi
    assert is_due(60, NOW - timedelta(minutes=60), NOW) is True
    # 90 dk once => vadesi gecti
    assert is_due(60, NOW - timedelta(minutes=90), NOW) is True


def test_select_due_monitors_filters_active_and_due():
    monitors = [
        _FakeMonitor(scan_interval_minutes=None),  # manuel -> haric
        _FakeMonitor(scan_interval_minutes=60, last_scanned_at=None),  # hic taranmadi -> dahil
        _FakeMonitor(scan_interval_minutes=60, last_scanned_at=NOW - timedelta(minutes=10)),  # erken -> haric
        _FakeMonitor(scan_interval_minutes=15, last_scanned_at=NOW - timedelta(minutes=20)),  # gecti -> dahil
        _FakeMonitor(is_active=False, scan_interval_minutes=15, last_scanned_at=None),  # pasif -> haric
    ]
    due = select_due_monitors(monitors, NOW)
    assert len(due) == 2
    assert all(m.is_active and m.scan_interval_minutes for m in due)


def test_allowed_scan_intervals():
    # API/arayuz ile uyumlu izinli araliklar
    assert 15 in ALLOWED_SCAN_INTERVALS
    assert 1440 in ALLOWED_SCAN_INTERVALS
    assert 7 not in ALLOWED_SCAN_INTERVALS


# --- Bulgu dedup (parmak izi) + bildirim esigi ---

def test_finding_fingerprint_is_deterministic_and_distinct():
    mid = "11111111-1111-1111-1111-111111111111"
    raw = {"candidate_domain": "markam-bahis.com", "category_hint": "gambling"}
    fp1 = finding_fingerprint("illegal_site", mid, raw)
    fp2 = finding_fingerprint("illegal_site", mid, dict(reversed(list(raw.items()))))
    assert fp1 == fp2  # anahtar sirasi onemsiz (kanonik)
    # Farkli ham veri -> farkli parmak izi
    assert fp1 != finding_fingerprint("illegal_site", mid, {**raw, "candidate_domain": "x.com"})
    # Farkli monitor -> farkli parmak izi
    assert fp1 != finding_fingerprint("illegal_site", "22222222-2222-2222-2222-222222222222", raw)


def test_severity_at_least():
    assert severity_at_least("high", "medium") is True
    assert severity_at_least("medium", "medium") is True
    assert severity_at_least("low", "medium") is False
    assert severity_at_least("critical", "info") is True
    # bilinmeyen deger -> bildir (True)
    assert severity_at_least("garip", "high") is True
