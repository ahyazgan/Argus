"""Canli dis API'lere karsi gercek entegrasyon testleri.

Bu testler GERCEK servislere ag uzerinden istek atar ve yalnizca ilgili kimlik bilgisi
(ortam degiskeni) tanimliysa calisir; aksi halde ATLANIR. Bu yuzden CI'da varsayilan
olarak yesil kalir (skipped). Yalnizca bunlari calistirmak icin:

    pytest -m integration

Gerekli ortam degiskenleri (yalnizca calistirmak istediklerin):
    HIBP_API_KEY          (+ ops. HIBP_TEST_ACCOUNT)
    SHODAN_API_KEY        (+ ops. SHODAN_TEST_IP, varsayilan 8.8.8.8)
    GITHUB_TEST_REPO + GITHUB_TEST_TOKEN   (DIKKAT: gercek bir issue olusturur)
    STRIPE_SECRET_KEY + STRIPE_TEST_PRICE  (Stripe TEST anahtari kullanin)
    CHAIN_ANALYSIS_API_KEY    (financial_crime -> OpenSanctions /match)
    COURT_RECORDS_API_KEY     (due_diligence -> OpenCorporates arama)
    RUN_LIVE_OSINT=1          (anahtarsiz ama AG gerektiren kaynaklar:
                               disinformation -> Google News RSS,
                               competitor_intel -> rakip ana sayfa)

Not: Konnektorler settings.* alanlarini okur; bu alanlar ilgili ortam
degiskenlerinden otomatik dolar. Bayrak gerektiren (anahtarsiz) kaynaklarda
test, ilgili settings bayragini gecici olarak acar (monkeypatch).
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("HIBP_API_KEY"), reason="HIBP_API_KEY tanimli degil")
def test_hibp_live_returns_breaches():
    from app.modules.darkweb.collectors import HIBPCollector

    account = os.getenv("HIBP_TEST_ACCOUNT", "account-exists@hibp-integration-tests.com")
    records = HIBPCollector().collect("email", account)
    assert isinstance(records, list)
    # Bilinen test hesabi icin sizinti beklenir; her kayit yapilandirilmis olmali
    for r in records:
        assert r["asset_value"] == account
        assert "breach_name" in r


@pytest.mark.skipif(not os.getenv("SHODAN_API_KEY"), reason="SHODAN_API_KEY tanimli degil")
def test_shodan_live_host_lookup():
    from app.modules.security_scan.collectors import ShodanCollector

    ip = os.getenv("SHODAN_TEST_IP", "8.8.8.8")
    records = ShodanCollector().collect("ip", ip)
    assert isinstance(records, list)
    for r in records:
        assert r["issue_type"] == "exposed_service"
        assert r["target"] == ip


@pytest.mark.skipif(
    not (os.getenv("GITHUB_TEST_REPO") and os.getenv("GITHUB_TEST_TOKEN")),
    reason="GITHUB_TEST_REPO/GITHUB_TEST_TOKEN tanimli degil",
)
def test_github_issue_live_creates_issue():
    from app.core_services.notifications.engine import create_github_issue, github_issue_payload

    repo = os.environ["GITHUB_TEST_REPO"]
    token = os.environ["GITHUB_TEST_TOKEN"]
    payload = github_issue_payload(
        "Entegrasyon testi", "low", "Argus canli test", "yok", "test.example.com"
    )
    assert create_github_issue(repo, token, payload) is True


@pytest.mark.skipif(
    not (os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_TEST_PRICE")),
    reason="STRIPE_SECRET_KEY/STRIPE_TEST_PRICE tanimli degil",
)
def test_stripe_checkout_live():
    import stripe

    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": os.environ["STRIPE_TEST_PRICE"], "quantity": 1}],
        success_url="https://example.com/ok",
        cancel_url="https://example.com/cancel",
        metadata={"organization_id": "test", "plan": "pro"},
    )
    assert session.url and session.url.startswith("https://")


@pytest.mark.skipif(
    not os.getenv("CHAIN_ANALYSIS_API_KEY"), reason="CHAIN_ANALYSIS_API_KEY tanimli degil"
)
def test_opensanctions_live_company_match():
    from app.modules.financial_crime.collectors import OpenSanctionsCollector

    company = os.getenv("OPENSANCTIONS_TEST_ENTITY", "Gazprom")
    records = OpenSanctionsCollector().collect("company", company)
    assert isinstance(records, list)
    for r in records:
        assert r["asset_value"] == company
        assert "signal_type" in r  # analyzer ile uyumlu sema


@pytest.mark.skipif(
    not os.getenv("COURT_RECORDS_API_KEY"), reason="COURT_RECORDS_API_KEY tanimli degil"
)
def test_opencorporates_live_company_search():
    from app.modules.due_diligence.collectors import OpenCorporatesCollector

    company = os.getenv("OPENCORPORATES_TEST_COMPANY", "Google")
    records = OpenCorporatesCollector().collect("company", company)
    assert isinstance(records, list)
    for r in records:
        assert "record_type" in r  # analyzer ile uyumlu sema


@pytest.mark.skipif(not os.getenv("RUN_LIVE_OSINT"), reason="RUN_LIVE_OSINT tanimli degil")
def test_google_news_live_returns_items(monkeypatch):
    from app.core.config import settings
    from app.modules.disinformation.collectors import GoogleNewsCollector

    monkeypatch.setattr(settings, "disinfo_news", True, raising=False)
    records = GoogleNewsCollector().collect("keyword", os.getenv("NEWS_TEST_QUERY", "bitcoin"))
    assert isinstance(records, list)
    for r in records:
        assert "claim" in r and r["asset_value"]  # analyzer ile uyumlu sema


@pytest.mark.skipif(not os.getenv("RUN_LIVE_OSINT"), reason="RUN_LIVE_OSINT tanimli degil")
def test_competitor_homepage_live(monkeypatch):
    from app.core.config import settings
    from app.modules.competitor_intel.collectors import HomepageWatchCollector

    monkeypatch.setattr(settings, "competitor_web_watch", True, raising=False)
    domain = os.getenv("COMPETITOR_TEST_DOMAIN", "example.com")
    records = HomepageWatchCollector().collect("domain", domain)
    assert isinstance(records, list)  # sinyal bulunmayabilir; sema bozulmamali


@pytest.mark.skipif(
    not os.getenv("SOCIAL_SEARCH_API_KEY"), reason="SOCIAL_SEARCH_API_KEY tanimli degil"
)
def test_social_search_live(monkeypatch):
    from app.core.config import settings
    from app.modules.social_media.collectors import SocialSearchCollector

    monkeypatch.setattr(settings, "social_search_api_key", os.environ["SOCIAL_SEARCH_API_KEY"], raising=False)
    records = SocialSearchCollector().collect("brand", os.getenv("SOCIAL_TEST_BRAND", "Markam"))
    assert isinstance(records, list)
    for r in records:
        assert "handle" in r and "impersonation_type" in r  # analyzer ile uyumlu sema
