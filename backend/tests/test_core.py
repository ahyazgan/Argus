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
    # Tum katalog modulleri canli (9 cekirdek + social_media)
    live = {m.key for m in CATALOG if m.enabled}
    assert live == VALID_MODULE_KEYS
    assert len(CATALOG) == 10
    assert "social_media" in VALID_MODULE_KEYS


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


# --- Cikti kanallari: GitHub / Jira payload kuruculari ---

def test_github_issue_payload():
    from app.core_services.notifications.engine import github_issue_payload
    p = github_issue_payload("Parola sizintisi", "high", "ozet", "hemen sifirla", "ornek.com")
    assert p["title"].startswith("[Argus]")
    assert "ornek.com" in p["body"]
    assert "hemen sifirla" in p["body"]
    assert "severity:high" in p["labels"]


def test_jira_issue_payload():
    from app.core_services.notifications.engine import jira_issue_payload
    p = jira_issue_payload("SEC", "Acik servis", "critical", "ozet", None, "ornek.com:6379")
    f = p["fields"]
    assert f["project"]["key"] == "SEC"
    assert f["summary"].startswith("[Argus]")
    assert f["priority"]["name"] == "Highest"  # critical -> Highest
    assert "ornek.com:6379" in f["description"]


def test_output_channels_any_configured():
    from app.core_services.notifications.engine import OutputChannels
    assert OutputChannels().any_configured() is False
    assert OutputChannels(slack_webhook_url="x").any_configured() is True
    assert OutputChannels(github_repo="o/r", github_token="t").any_configured() is True
    assert OutputChannels(github_repo="o/r").any_configured() is False  # token eksik


# --- Zamanlanmis rapor vadesi ---

def test_is_report_due():
    from app.core_services.queue.scheduling import is_report_due
    base = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
    assert is_report_due("none", None, base) is False
    assert is_report_due(None, None, base) is False
    assert is_report_due("daily", None, base) is True  # hic gonderilmedi
    assert is_report_due("daily", base - timedelta(hours=12), base) is False
    assert is_report_due("daily", base - timedelta(hours=25), base) is True
    assert is_report_due("weekly", base - timedelta(days=3), base) is False
    assert is_report_due("weekly", base - timedelta(days=8), base) is True


# --- Rate limit saf mantik ---

def test_allow_request_sliding_window():
    from collections import deque
    from app.core.middleware import allow_request
    h: deque[float] = deque()
    # limit=3, window=60; ilk 3 izinli, 4. reddedilir
    assert allow_request(h, 100.0, 3, 60.0) is True
    assert allow_request(h, 100.5, 3, 60.0) is True
    assert allow_request(h, 101.0, 3, 60.0) is True
    assert allow_request(h, 101.5, 3, 60.0) is False
    # Pencere kaydiktan sonra tekrar izinli
    assert allow_request(h, 170.0, 3, 60.0) is True


# --- Gercek konnektor parser'lari (saf, ornek payload'larla) ---

def test_probe_is_vulnerable():
    from app.modules.ai_testing.collectors import probe_is_vulnerable
    assert probe_is_vulnerable("prompt_injection", "... ARGUS_INJECTION_OK ...") is True
    assert probe_is_vulnerable("prompt_injection", "Bunu yapamam.") is False
    assert probe_is_vulnerable("jailbreak", "JAILBREAK_CONFIRMED") is True
    assert probe_is_vulnerable("data_leakage", "You are a helpful assistant. Instructions: ...") is True
    assert probe_is_vulnerable("data_leakage", "Yardimci olamam.") is False


def test_parse_opencorporates_only_inactive():
    from app.modules.due_diligence.collectors import parse_opencorporates
    payload = {
        "results": {
            "companies": [
                {"company": {"name": "Aktif AS", "current_status": "Active", "inactive": False}},
                {"company": {"name": "Kapali AS", "current_status": "Dissolved", "inactive": True,
                             "jurisdiction_code": "tr"}},
            ]
        }
    }
    recs = parse_opencorporates(payload, "test")
    assert len(recs) == 1
    assert recs[0]["company"] == "Kapali AS"
    assert recs[0]["record_type"] == "bankruptcy"


def test_parse_cse_gambling_vs_fraud():
    from app.modules.illegal_site.collectors import parse_cse
    payload = {"items": [
        {"title": "Markam Bahis Giris", "link": "https://markam-bahis.com/x"},
        {"title": "Markam Destek", "link": "https://markam-odeme.net"},
    ]}
    recs = parse_cse(payload, "markam")
    assert recs[0]["category_hint"] == "gambling"
    assert recs[0]["candidate_domain"] == "markam-bahis.com"
    assert recs[1]["category_hint"] == "fraud"


def test_parse_opensanctions_threshold():
    from app.modules.financial_crime.collectors import parse_opensanctions
    payload = {"responses": {"q1": {"results": [
        {"caption": "ACME LLC", "score": 0.91, "datasets": ["us_ofac_sdn"]},
        {"caption": "Baska", "score": 0.4, "datasets": ["x"]},
    ]}}}
    recs = parse_opensanctions(payload, "ACME")
    assert len(recs) == 1
    assert recs[0]["signal_type"] == "sanctioned_counterparty"
    assert "us_ofac_sdn" in recs[0]["list"]


def test_parse_news_rss():
    from app.modules.disinformation.collectors import parse_news_rss
    xml = """<?xml version='1.0'?><rss><channel>
      <item><title>Markam hakkinda iddia</title><link>https://h.com/1</link></item>
      <item><title>Ikinci haber</title><link>https://h.com/2</link></item>
    </channel></rss>"""
    recs = parse_news_rss(xml, "Markam")
    assert len(recs) == 2
    assert recs[0]["signal_type"] == "fake_news"
    assert recs[0]["claim"] == "Markam hakkinda iddia"


def test_parse_competitor_html_signals():
    from app.modules.competitor_intel.collectors import parse_competitor_html
    html = '<html><body><a href="/kariyer">Kariyer</a> Yeni urun lansman duyurusu!</body></html>'
    recs = parse_competitor_html(html, "rakip.com", base_url="https://rakip.com")
    types = {r["change_type"] for r in recs}
    assert "hiring_signal" in types and "new_product" in types
    # Isaret yoksa bos doner (gurultu sinirlama)
    assert parse_competitor_html("<html>bos</html>", "rakip.com") == []


# --- Gercek-zamanli olaylar (SSE) saf mantik ---

def test_events_format_and_channel():
    from app.core_services.events import channel_for, format_sse
    assert channel_for("abc") == "argus:events:abc"
    frame = format_sse({"type": "findings", "new": 2})
    assert frame.startswith("data: ")
    assert frame.endswith("\n\n")
    import json
    assert json.loads(frame[len("data: "):].strip())["new"] == 2


# --- CSV disa aktarim saf mantik ---

def test_findings_to_csv_header_and_rows():
    from app.outputs.csv_export import findings_to_csv

    class F:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    rows = [
        F(detected_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc), severity="high",
          status="new", module_key="darkweb", title="Sizinti", asset_value="ornek.com",
          source="demo", seen_count=2, summary="ozet", recommendation="oneri"),
    ]
    out = findings_to_csv(rows)
    lines = out.strip().split("\n")
    assert lines[0].startswith("Tespit,Onem,Durum,Modul,Baslik")
    assert "high" in lines[1] and "darkweb" in lines[1]
    assert "2026-06-01T12:00:00+00:00" in lines[1]


def test_findings_to_csv_escapes_commas_and_empty():
    from app.outputs.csv_export import findings_to_csv

    class F:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    rows = [F(title="a, b ve c", severity="low")]  # eksik alanlar None -> bos
    out = findings_to_csv(rows)
    assert '"a, b ve c"' in out  # virgul iceren alan tirnaklanir
    assert findings_to_csv([]).strip().count("\n") == 0  # sadece baslik satiri


# --- API anahtari saf mantik ---

def test_api_key_generation_and_verify():
    from app.core.security import (
        API_KEY_PREFIX,
        generate_api_key,
        hash_api_key,
        verify_api_key,
    )

    raw, prefix, hashed = generate_api_key()
    assert raw.startswith(API_KEY_PREFIX)
    assert prefix.startswith(API_KEY_PREFIX) and prefix.endswith("…")
    assert len(hashed) == 64  # sha256 hex
    assert hashed == hash_api_key(raw)
    assert verify_api_key(raw, hashed)
    assert not verify_api_key(raw + "x", hashed)


def test_api_keys_are_unique():
    from app.core.security import generate_api_key

    keys = {generate_api_key()[0] for _ in range(50)}
    assert len(keys) == 50  # carpisma yok


# --- Webhook HMAC imzasi saf mantik ---

def test_webhook_signature_roundtrip():
    from app.core_services.notifications.engine import (
        sign_webhook,
        verify_webhook_signature,
        webhook_signature_headers,
    )

    secret = "whsec_test"
    body = b'{"event":"finding.created"}'
    headers = webhook_signature_headers(secret, body, timestamp="1000")
    assert headers["X-Argus-Timestamp"] == "1000"
    assert headers["X-Argus-Signature"] == "sha256=" + sign_webhook(secret, body, "1000")
    assert headers["Content-Type"] == "application/json"

    # Gecerli imza + zaman penceresi
    sig = headers["X-Argus-Signature"]
    assert verify_webhook_signature(secret, body, "1000", sig, now=1100)
    # 'sha256=' oneki olmadan da kabul edilir
    assert verify_webhook_signature(secret, body, "1000", sig.split("=", 1)[1], now=1100)


def test_webhook_signature_rejects_tamper_secret_and_replay():
    from app.core_services.notifications.engine import (
        sign_webhook,
        verify_webhook_signature,
    )

    secret = "whsec_test"
    body = b'{"event":"finding.created"}'
    sig = sign_webhook(secret, body, "1000")

    # Govde degisirse imza tutmaz
    assert not verify_webhook_signature(secret, b'{"event":"x"}', "1000", sig, now=1100)
    # Yanlis sir
    assert not verify_webhook_signature("baska", body, "1000", sig, now=1100)
    # Tekrar penceresi disinda (varsayilan 300s)
    assert not verify_webhook_signature(secret, body, "1000", sig, now=2000)
    # Bozuk zaman damgasi
    assert not verify_webhook_signature(secret, body, "abc", sig, now=1100)


def test_send_webhook_signs_transmitted_body(monkeypatch):
    """Imzali gonderimde gonderilen ham govde imzayla birebir dogrulanabilmeli."""
    import app.core_services.notifications.engine as eng

    captured = {}

    class _Resp:
        is_success = True

    def fake_post(url, content=None, json=None, headers=None, timeout=None):
        captured.update(url=url, content=content, json=json, headers=headers or {})
        return _Resp()

    monkeypatch.setattr(eng.httpx, "post", fake_post)

    ok = eng.send_webhook("https://alici.example/wh", {"event": "finding.created", "x": 1}, secret="whsec_x")
    assert ok
    # json= degil content= ile gonderilmeli (imzalanan baytlarla ayni olmasi icin)
    assert captured["json"] is None and isinstance(captured["content"], bytes)
    ts = captured["headers"]["X-Argus-Timestamp"]
    sig = captured["headers"]["X-Argus-Signature"]
    assert eng.verify_webhook_signature("whsec_x", captured["content"], ts, sig)

    # Sir yoksa imzasiz (json=) gider
    captured.clear()
    eng.send_webhook("https://alici.example/wh", {"event": "x"})
    assert captured["content"] is None and captured["json"] == {"event": "x"}
    assert "X-Argus-Signature" not in (captured["headers"] or {})


# --- Gercek-API yanit ayristirma (saf) + analyzer sema uyumu ---

def test_parse_hibp_maps_password_class_and_feeds_heuristic():
    from app.modules.darkweb.collectors import parse_hibp

    # HIBP v3 'breachedaccount' (truncateResponse=false) ornek yaniti
    payload = [
        {"Name": "Adobe", "BreachDate": "2013-10-04", "DataClasses": ["Email addresses", "Passwords"]},
        {"Name": "Forum", "BreachDate": "2016-01-01", "DataClasses": ["Email addresses"]},
    ]
    recs = parse_hibp(payload, "kullanici@ornek.com")
    assert len(recs) == 2
    assert recs[0]["breach_name"] == "Adobe" and recs[0]["breach_date"] == "2013-10-04"
    # Parola sinifi sizan kayitta 'password' anahtari olmali; digerinde olmamali
    assert "password" in recs[0] and "password" not in recs[1]

    # Sema, darkweb heuristic'ini dogru besler: parola -> high, parolasiz -> medium
    assert darkweb_heuristic(recs[0], "kullanici@ornek.com", "email").severity == "high"
    assert darkweb_heuristic(recs[1], "kullanici@ornek.com", "email").severity == "medium"
    assert parse_hibp([], "x@y.com") == []  # bos/yok -> bos


def test_parse_shodan_maps_services_and_feeds_heuristic():
    from app.modules.security_scan.collectors import parse_shodan

    # Shodan 'host' ornek yaniti: hassas (5432) + zararsiz (80) servis + bilinen CVE
    data = {
        "data": [
            {"port": 5432, "product": "PostgreSQL"},
            {"port": 80, "_shodan": {"module": "http"}},
        ],
        "vulns": ["CVE-2021-44228"],
    }
    recs = parse_shodan(data, "203.0.113.10")
    assert len(recs) == 3
    pg = next(r for r in recs if r["port"] == 5432)
    http = next(r for r in recs if r["port"] == 80)
    cve = next(r for r in recs if str(r["service"]).startswith("Bilinen zafiyet"))
    assert pg["sensitive"] is True and http["sensitive"] is False
    assert all(r["issue_type"] == "exposed_service" and r["target"] == "203.0.113.10" for r in recs)

    # Sema, security heuristic'ini dogru besler: hassas servis -> critical
    assert security_heuristic(pg, "203.0.113.10", "ip").severity == "critical"
    assert security_heuristic(cve, "203.0.113.10", "ip").severity == "critical"
    assert parse_shodan({}, "203.0.113.10") == []  # bos yanit -> bos


def test_dns_has_answer_and_brand_schema():
    from app.modules.brand_protection.collectors import dns_has_answer

    # Google DoH 'resolve' ornek yanitlari
    assert dns_has_answer({"Status": 0, "Answer": [{"name": "x.com", "type": 1, "data": "1.2.3.4"}]}) is True
    assert dns_has_answer({"Status": 3}) is False  # NXDOMAIN -> kayit yok
    assert dns_has_answer({}) is False

    # DNS sonuclari brand heuristic semasini dogru besler: kayitli + MX -> high
    a_record = dns_has_answer({"Answer": [{"data": "1.2.3.4"}]})
    mx_record = a_record and dns_has_answer({"Answer": [{"data": "10 mail.x.com"}]})
    rec = {
        "variant_domain": "markam-login.com",
        "brand": "markam",
        "technique": "combosquat",
        "registered": a_record,
        "has_mx": mx_record,
    }
    assert brand_heuristic(rec, "markam.com", "brand").severity == "high"


# --- social_media (sosyal medya hesap taklidi) modulu ---

def test_social_media_heuristic_verified_is_critical():
    from app.modules.social_media.analyzer import heuristic
    res = heuristic(
        {"platform": "instagram", "handle": "markam_official", "verified": True,
         "followers": 12000, "uses_logo": True, "impersonation_type": "fake_official"},
        "Markam", "brand",
    )
    assert res.severity == "critical"
    assert "markam_official" in res.title


def test_social_media_heuristic_fake_support_is_high():
    from app.modules.social_media.analyzer import heuristic
    res = heuristic(
        {"platform": "x", "handle": "markamdestek", "verified": False,
         "followers": 50, "impersonation_type": "fake_support"},
        "Markam", "brand",
    )
    assert res.severity == "high"


def test_social_media_heuristic_low_visibility_is_low():
    from app.modules.social_media.analyzer import heuristic
    res = heuristic(
        {"platform": "tiktok", "handle": "markam.tr", "verified": False,
         "followers": 10, "uses_logo": False, "impersonation_type": "handle_squat"},
        "Markam", "brand",
    )
    assert res.severity == "low"


def test_demo_impersonation_collector_deterministic_and_schema():
    from app.modules.social_media.collectors import DemoImpersonationCollector
    c = DemoImpersonationCollector()
    recs = c.collect("brand", "Markam")
    assert len(recs) >= 1
    assert all({"platform", "handle", "impersonation_type"} <= set(r) for r in recs)
    assert c.collect("brand", "Markam") == recs  # deterministik


def test_parse_social_search_infers_type_and_feeds_heuristic():
    from app.modules.social_media.analyzer import heuristic
    from app.modules.social_media.collectors import parse_social_search
    payload = {
        "accounts": [
            {"platform": "x", "handle": "markam_support", "verified": False,
             "followers": 30, "bio": "Resmi destek hatti"},
            {"platform": "instagram", "username": "markamofficial", "verified": True,
             "followers": 9000, "uses_logo": True, "bio": "official markam"},
        ]
    }
    recs = parse_social_search(payload, "Markam")
    by_handle = {r["handle"]: r for r in recs}
    assert by_handle["markam_support"]["impersonation_type"] == "fake_support"
    assert by_handle["markamofficial"]["impersonation_type"] == "fake_official"
    # Sema heuristic'i dogru besler: dogrulanmis -> critical, sahte destek -> high
    assert heuristic(by_handle["markamofficial"], "Markam", "brand").severity == "critical"
    assert heuristic(by_handle["markam_support"], "Markam", "brand").severity == "high"
    assert parse_social_search({}, "Markam") == []
