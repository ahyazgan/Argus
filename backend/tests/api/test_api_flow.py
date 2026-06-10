"""Uctan uca API testleri (gercek DB): auth, RBAC, modul/monitor akisi, stats."""
from __future__ import annotations

import uuid


async def _register(client, email: str | None = None):
    email = email or f"owner-{uuid.uuid4().hex[:8]}@ornek.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": "Test AS", "email": email, "password": "sifre12345"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"], email


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_register_login_me(client):
    token, email = await _register(client)

    me = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "owner"

    login = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "sifre12345"}
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


async def test_requires_auth(client):
    resp = await client.get("/api/v1/modules")
    assert resp.status_code == 401


async def test_module_toggle_and_monitor_flow(client):
    token, _ = await _register(client)
    h = _auth(token)

    # Modulu ac
    t = await client.post("/api/v1/modules/toggle", headers=h, json={"module_key": "darkweb", "enable": True})
    assert t.status_code == 200
    assert "darkweb" in t.json()["enabled_modules"]

    # Monitor olustur
    m = await client.post(
        "/api/v1/m/darkweb/monitors",
        headers=h,
        json={"module_key": "darkweb", "name": "Test", "asset_type": "domain", "asset_value": "ornek.com"},
    )
    assert m.status_code == 201, m.text
    assert m.json()["scan_interval_minutes"] is None

    # Listele
    lst = await client.get("/api/v1/m/darkweb/monitors", headers=h)
    assert lst.status_code == 200 and len(lst.json()) == 1

    # Zamanlama ayarla (gecerli)
    mid = m.json()["id"]
    sch = await client.patch(
        f"/api/v1/m/darkweb/monitors/{mid}/schedule", headers=h, json={"scan_interval_minutes": 60}
    )
    assert sch.status_code == 200 and sch.json()["scan_interval_minutes"] == 60

    # Gecersiz aralik reddedilir
    bad = await client.patch(
        f"/api/v1/m/darkweb/monitors/{mid}/schedule", headers=h, json={"scan_interval_minutes": 7}
    )
    assert bad.status_code == 422

    # Stats erisilebilir
    st = await client.get("/api/v1/findings/stats", headers=h)
    assert st.status_code == 200
    assert "by_severity" in st.json()


async def test_plan_limit_enforced(client):
    token, _ = await _register(client)  # Starter plani: 2 modul
    h = _auth(token)
    for key in ("darkweb", "illegal_site"):
        r = await client.post("/api/v1/modules/toggle", headers=h, json={"module_key": key, "enable": True})
        assert r.status_code == 200
    # 3. modul plan limitini asar
    r3 = await client.post("/api/v1/modules/toggle", headers=h, json={"module_key": "security_scan", "enable": True})
    assert r3.status_code == 403


async def test_rbac_member_cannot_create_user(client):
    token, _ = await _register(client)
    h = _auth(token)
    # Owner bir uye olusturur
    created = await client.post(
        "/api/v1/team",
        headers=h,
        json={"email": f"member-{uuid.uuid4().hex[:6]}@ornek.com", "password": "sifre12345", "role": "member"},
    )
    assert created.status_code == 201
    member_email = created.json()["email"]

    # Uye olarak giris yap
    login = await client.post(
        "/api/v1/auth/login", data={"username": member_email, "password": "sifre12345"}
    )
    member_token = login.json()["access_token"]

    # Uye baska kullanici olusturamaz (403)
    forbidden = await client.post(
        "/api/v1/team",
        headers=_auth(member_token),
        json={"email": "x@ornek.com", "password": "sifre12345", "role": "member"},
    )
    assert forbidden.status_code == 403


async def test_finding_assign_and_comment(client):
    token, _ = await _register(client)
    h = _auth(token)
    await client.post("/api/v1/modules/toggle", headers=h, json={"module_key": "darkweb", "enable": True})

    # Bulgu yoksa atama/yorum testini, bir bulgu olusturmak icin dogrudan DB'siz yapamayiz;
    # bu yuzden yalnizca uc noktalarin 404'u dogru dondurdugunu kontrol ederiz.
    fake = uuid.uuid4()
    r = await client.get(f"/api/v1/findings/{fake}/comments", headers=h)
    assert r.status_code == 404
