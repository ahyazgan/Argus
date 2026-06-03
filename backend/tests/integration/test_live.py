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

Not: HIBP/Shodan konnektorleri settings.{hibp,shodan}_api_key okur; bu alanlar ilgili
ortam degiskenlerinden otomatik dolar.
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
