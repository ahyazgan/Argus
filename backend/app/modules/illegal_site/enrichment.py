"""Yasadisi site tespiti - anahtarsiz GERCEK sinyal toplayicilar (zenginlestirme).

Buradaki yardimcilarin tamami halka acik, anahtarsiz kaynaklara dayanir ve
SAVUNMA amaclidir: yalnizca musterinin markasini/varligini istismar eden supheli
ADAY alan adlarini dogrular ve kanit toplar. Yasadisi pazar yeri tarayicisi /
saldiri ICERMEZ.

- _doh_query: Google DNS-over-HTTPS ile bir kaydin (A/MX) varligini sorgular.
- crt_sh_domains: Certificate Transparency loglarindan (crt.sh) markayi iceren,
  yeni SSL sertifikali alan adlarini cikarir.
- fetch_content_signals: aday siteyi cekip kumar/dolandiricilik anahtar kelimelerini
  ve olasi sahte odeme/giris formunu (kanit) tespit eder.
- rdap_age_days: RDAP ile alan adinin kayit yasini (gun) hesaplar - yeni kayit yuksek risktir.
- enrich_domain: yukaridakileri tek bir sinyal sozlugunde birlestirir.

Her cagri ag hatasina dayaniklidir (hata/zaman asiminda guvenli varsayilan doner),
boylece tarama akisi asla bozulmaz.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

_UA = {"user-agent": "Argus-Intelligence (defensive brand-abuse monitoring)"}

# Aday site iceriginde aranan supheli anahtar kelimeler (kumar/bahis ve dolandiricilik).
GAMBLING_KEYWORDS = [
    "bahis", "casino", "slot", "bonus", "canli bahis", "deposit", "rulet", "poker",
]
FRAUD_KEYWORDS = [
    "giris yap", "sifre", "kart numarasi", "cvv", "iban", "dogrulama kodu",
    "odeme onayla", "tc kimlik",
]
# Sahte odeme/giris formu isareti olabilecek HTML ipuclari.
_FORM_HINTS = ["type=\"password\"", "type='password'", "name=\"cardnumber\"", "card-number"]


def _doh_query(name: str, rtype: str) -> bool:
    """Google DNS-over-HTTPS ile bir kaydin (A/MX) var olup olmadigini sorgular.

    Anahtarsiz gercek DNS dogrulamasi. Hata/zaman asiminda False doner (akisi bozmaz).
    """
    try:
        resp = httpx.get(
            "https://dns.google/resolve",
            params={"name": name, "type": rtype},
            timeout=8.0,
        )
        return bool(resp.json().get("Answer"))
    except (httpx.HTTPError, ValueError):
        return False


def crt_sh_domains(brand: str, limit: int = 10) -> list[str]:
    """Certificate Transparency loglarindan (crt.sh) markayi iceren alan adlarini doner.

    Anahtarsiz ve ucretsiz. Kumar/dolandiricilik siteleri cogu zaman yeni SSL sertifikasi
    aldigindan CT loglari erken tespit icin etkili bir kaynaktir. Hata durumunda bos doner.
    """
    label = brand.lower().strip().replace(" ", "").partition(".")[0]
    if len(label) < 3:
        return []
    try:
        resp = httpx.get(
            "https://crt.sh/",
            params={"q": f"%{label}%", "output": "json"},
            headers=_UA,
            timeout=15.0,
        )
        resp.raise_for_status()
        rows = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    seen: list[str] = []
    for row in rows:
        for name in str(row.get("name_value", "")).splitlines():
            name = name.strip().lstrip("*.").lower()
            # Markanin gercek alan adini ve gecersiz girdileri ele
            if name and label in name and name not in seen:
                seen.append(name)
                if len(seen) >= limit:
                    return seen
    return seen


def fetch_content_signals(domain: str) -> dict:
    """Aday siteyi cekip kumar/dolandiricilik kanit sinyallerini cikarir.

    Doner: {reachable, keyword_hits[], gambling_hits, fraud_hits, has_payment_form, title}.
    Ulasilmazsa {"reachable": False} doner (akisi bozmaz).
    """
    html = ""
    reachable = False
    for scheme in ("https", "http"):
        try:
            resp = httpx.get(
                f"{scheme}://{domain}", headers=_UA, timeout=10.0, follow_redirects=True
            )
            html = resp.text[:200_000]
            reachable = True
            break
        except httpx.HTTPError:
            continue
    if not reachable:
        return {"reachable": False}

    low = html.lower()
    gambling_hits = [k for k in GAMBLING_KEYWORDS if k in low]
    fraud_hits = [k for k in FRAUD_KEYWORDS if k in low]
    has_payment_form = any(h in low for h in _FORM_HINTS)
    title = ""
    if "<title" in low:
        start = low.find(">", low.find("<title")) + 1
        end = low.find("</title>", start)
        if 0 < start < end:
            title = html[start:end].strip()[:160]
    return {
        "reachable": True,
        "keyword_hits": gambling_hits + fraud_hits,
        "gambling_hits": len(gambling_hits),
        "fraud_hits": len(fraud_hits),
        "has_payment_form": has_payment_form,
        "title": title,
    }


def rdap_age_days(domain: str) -> int | None:
    """RDAP (rdap.org) ile alan adinin kayit yasini gun olarak doner. Hata: None."""
    try:
        resp = httpx.get(f"https://rdap.org/domain/{domain}", headers=_UA, timeout=10.0)
        resp.raise_for_status()
        events = resp.json().get("events", []) or []
    except (httpx.HTTPError, ValueError):
        return None
    for ev in events:
        if ev.get("eventAction") == "registration" and ev.get("eventDate"):
            try:
                reg = datetime.fromisoformat(ev["eventDate"].replace("Z", "+00:00"))
                return max(0, (datetime.now(timezone.utc) - reg).days)
            except ValueError:
                return None
    return None


def enrich_domain(domain: str) -> dict:
    """Bir aday alan adi icin tum anahtarsiz gercek sinyalleri birlestirir.

    Ag cagrilari icerir; cagiran taraf bunu bir bayrakla (illegal_live_enrich) kapatabilir.
    Hata/zaman asimi tek tek yutulur; eksik sinyaller atlanir.
    """
    signals = fetch_content_signals(domain)
    signals["registered"] = _doh_query(domain, "A")
    signals["has_mx"] = signals["registered"] and _doh_query(domain, "MX")
    signals["domain_age_days"] = rdap_age_days(domain)
    return signals
