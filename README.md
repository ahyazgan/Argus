# Argus Intelligence

![CI](https://github.com/ahyazgan/Argus/actions/workflows/ci.yml/badge.svg)

**Tek platform — sonsuz modül — bir abonelik.** OSINT & tehdit istihbaratı SaaS platformu.

Ortak bir çekirdeği (auth, görev kuyruğu, Claude AI motoru, bildirim, ödeme) paylaşan,
müşteriye göre açılıp kapanan modüllerden ve tek tip bir çıktı katmanından oluşur.

Bu repo, mimariyi uçtan uca kanıtlayan bir **dikey dilim (MVP)** içerir:
ortak çekirdek + **9 canlı modül** (kataloğun tamamı: Dark web izleme, Yasadışı site
tespiti, Güvenlik tarama, Marka koruma, Finansal suç tespiti, Rakip istihbarat,
Dezenformasyon tespiti, Due diligence, AI sistem testi) + dashboard + PDF/REST çıktısı.
Modüller ortak, modülden-bağımsız bir tarama
motorunu ve genel API'yi (`/api/v1/m/{module_key}/...`) paylaşır.

---

## Mimari

```
Ortak çekirdek (core_services/)        Modüller (modules/)            Çıktı (outputs/ + api/)
├─ OSINT toplayıcı (osint/)            ├─ base.py  (Module ABC +      ├─ Dashboard (Next.js)
├─ Claude AI motoru (claude_engine/)   │           kayıt defteri)     ├─ PDF rapor (WeasyPrint)
├─ Async kuyruk (queue/ — Celery)      ├─ catalog.py (9 modül)        ├─ REST API (FastAPI)
│   + genel tarama görevi              ├─ darkweb/          ← CANLI   └─ Webhook / Slack
│   + zamanlanmış dispatcher (beat)    │
├─ Bildirim (notifications/)           ├─ illegal_site/     ← CANLI
└─ Multi-tenant auth (core/)           ├─ security_scan/    ← CANLI
                                       ├─ brand_protection/ ← CANLI
                                       ├─ financial_crime/  ← CANLI
                                       ├─ competitor_intel/ ← CANLI
                                       ├─ disinformation/   ← CANLI
                                       ├─ due_diligence/    ← CANLI
                                       └─ ai_testing/       ← CANLI
```

- **Genişleme:** Yeni bir modül = `modules/<ad>/` (`collectors.py` + `analyzer.py` +
  `module.py` kendini `register()` eder) + `catalog.py` içinde `enabled=True` +
  `modules/__init__.py` `load_modules()`'a bir import. Çekirdek (görev, API, motor) değişmez —
  genel tarama görevi ve `/m/{module_key}/...` API'si tüm modüller için çalışır.
- **Multi-tenancy:** Her tablo `organization_id` ile kapsanır; `require_module("darkweb")`
  bağımlılığı modül erişimini, plan limiti modül sayısını dayatır.

### Teknoloji
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async/asyncpg), Celery + Redis,
  Anthropic Claude SDK, WeasyPrint, PostgreSQL
- **Frontend:** Next.js 14 (App Router), React, Tailwind
- **Altyapı:** Docker Compose

---

## Kurulum & çalıştırma (Docker — önerilen)

Gereken: **Docker Desktop**.

```bash
# 1) Ortam dosyasını oluştur
cp .env.example .env
#    İsteğe bağlı: .env içine ANTHROPIC_API_KEY ekleyin.
#    (Anahtar yoksa Claude motoru sezgisel fallback ile çalışır — demo anahtarsız da çalışır.)

# 2) Hepsini ayağa kaldır
docker compose up --build
```

Servisler:
- Backend API: http://localhost:8000  · OpenAPI doküman: http://localhost:8000/docs
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432 · Redis: localhost:6379

> Tablolar açılışta otomatik oluşturulur (`create_all`). Üretim için Alembic baseline'ı
> hazırdır (`alembic/versions/0001_initial.py`): `docker compose exec backend alembic upgrade head`.
> Sonraki şema değişikliklerinde `alembic revision --autogenerate -m "..."` kullanın.

---

## Demo akışı (uçtan uca)

1. http://localhost:3000 → **Kayıt ol** (kurum adı + e-posta + parola). Otomatik olarak
   bir Organization + owner kullanıcı + Starter abonelik oluşur.
2. **Modüller** sayfasında **Dark web izleme**’yi **Aç** (Starter planı 2 modüle izin verir).
3. **Dark web izleme** sayfasında bir monitör ekleyin (örn. tip `domain`, değer `ornek.com`).
4. Monitörde **Tara**’ya basın → Celery görevi arka planda çalışır.
   Dilerseniz monitörün **Otomatik** sıklığını (15 dk / 1 sa / 6 sa / 24 sa) seçin →
   Celery **beat** vadesi gelen monitörleri kendiliğinden tarar (manuel tetikleme gerekmez).
5. Demo konnektör + Claude triyajı bulgular üretir (önem + Türkçe özet + öneri).
6. **PDF rapor indir** → WeasyPrint ile Türkçe rapor.
7. **Ayarlar**’da webhook/Slack URL’i tanımlayın → yeni bulguda bildirim gönderilir.
8. **Abonelik**’te plan limitini test edin (limit aşımı reddedilir).

> **Zamanlanmış taramalar:** `beat` servisi her dakika (`SCAN_BEAT_INTERVAL_SECONDS`)
> vadesi gelmiş tüm aktif monitörleri tek bir modülden-bağımsız dispatcher
> (`core.scan_due_monitors`) ile tarar — 9 modülün hepsi için çalışır. Tablo şeması
> değiştiğinden, mevcut bir veritabanı için Alembic migration’ı çalıştırın (taze DB’de
> `create_all` yeni kolonları otomatik ekler).

> Aynı akış **Yasadışı site tespiti** modülü için de geçerlidir: Modüller’den açın, sol
> menüden modüle girin, bir marka/anahtar kelime (örn. `markam`) ekleyip tarayın → kumar/
> dolandırıcılık şüpheli siteleri + BTK ihbar önerisi içeren bulgular üretilir. Yeni modüller
> sol menüde otomatik belirir.

---

## Testler

```bash
docker compose exec backend pytest                  # çekirdek birim testleri (DB'siz)
docker compose exec backend pytest tests/api         # DB'li uçtan uca API testleri
docker compose exec backend pytest -m integration    # canlı API testleri (kimlik bilgisi gerektirir)
```

- **Çekirdek birim testleri** (`tests/test_core.py`, DB'siz): slugify, parola hash, plan
  limitleri, modül katalogu, sezgisel triyaj, demo konnektör, bulgu parmak izi/eşik, çıktı
  payload'ları, zamanlama + rapor vade mantığı, rate-limit penceresi.
- **API testleri** (`tests/api/`): FastAPI ASGI + gerçek Postgres üzerinden uçtan uca akış
  (auth, RBAC, modül/monitör, plan limiti, stats). `DATABASE_URL` yoksa atlanır; CI'da bir
  postgres servisi ile koşar.
- **Entegrasyon testleri** (`tests/integration/`): gerçek HIBP / Shodan / GitHub / Stripe
  API'lerine vurur; ilgili ortam değişkeni yoksa atlanır. `pytest -m integration`.

---

## Notlar / sınırlar

- **Etik/yasal:** Dark web modülü **savunma amaçlıdır** — yalnızca müşterinin *kendi*
  varlıkları için, yasal/halka açık kaynaklardan sızıntı izler. Yasadışı pazar yeri
  tarayıcısı / Tor crawler içermez.
- **Demo konnektörü** anahtarsız çalışır (deterministik örnek). Konnektör durumu:

  | Modül | Gerçek kaynak | Durum |
  |---|---|---|
  | darkweb | HaveIBeenPwned (`HIBP_API_KEY`) | ✅ gerçek API bağlı |
  | security_scan | Shodan (`SHODAN_API_KEY`) | ✅ gerçek API bağlı |
  | brand_protection | DNS-over-HTTPS (`BRAND_DNS_CHECK=true`) | ✅ gerçek, anahtarsız |
  | illegal_site / financial_crime / competitor_intel / disinformation / due_diligence / ai_testing | arama/zincir/scrape/sosyal/sicil/uç-nokta API'leri | ⏳ entegrasyon noktası hazır (stub); sağlayıcı anahtarı gerektirir |

  Anahtar/sağlayıcı yoksa ilgili modül deterministik demo konnektörüne düşer (demo akışı bozulmaz).
- **Stripe** gerçek akış için hazır: `STRIPE_ENABLED=true` + `STRIPE_SECRET_KEY` +
  `STRIPE_PRICE_*` ile checkout oturumu açılır, `/billing/webhook` imza doğrulayıp
  aboneliği günceller. Kapalıyken stub döner (plan limiti dayatması yine çalışır).
- **Çıktı kanalları:** Dashboard, PDF, REST, Webhook/Slack, **GitHub Issues**, **Jira**,
  e-posta ve **kamu/BTK ihbar** kanalı canlı (kurum ayarlarından yapılandırılır). BTK İhbarweb'in
  açık API'si olmadığından kamu kanalı, yapılandırılabilir bir uç noktaya (uyum/e-Devlet relay)
  yapılandırılmış ihbar gönderir; modüle göre BTK/MASAK/USOM işaretler.
- **Çok kullanıcılı:** Organizasyon başına kullanıcılar ve roller (Sahip/Yönetici/Üye); Ekip
  sayfasından yönetilir, rol bazlı yetki (`require_role`) backend'de dayatılır.
- **Windows yerel (Docker'sız) çalıştırma:** Celery için `--pool=solo`, WeasyPrint için GTK
  bağımlılıkları gerekir; bu yüzden birincil yol Docker'dır.

---

## Yol haritası (sonraki dilimler)

- ~~Kataloğun 9 modülü~~ — **tamamlandı:** 9/9 modül canlı, hepsi aynı çekirdeğe takılı
- ~~Zamanlanmış (periyodik) taramalar (Celery beat)~~ — **tamamlandı:** monitör başına
  otomatik tarama sıklığı + `beat` dispatcher (tüm modüller için)
- ~~Bulgu yinelenme önleme (dedup) + bildirim eşiği~~ — **tamamlandı**
- ~~Jira/GitHub ticket çıktı kanalları + e-posta~~ — **tamamlandı** (BTK/kamu API kaldı)
- ~~Gerçek Stripe checkout + webhook'ları~~ — **tamamlandı** (kimlik bilgisi gerektirir)
- ~~Gerçek dark web / sızıntı feed entegrasyonları~~ — **tamamlandı:** HIBP + Shodan
  (API anahtarı gerektirir; anahtarsız demo konnektör çalışır)
- CI + Alembic baseline + bağımlılık pinleri — **tamamlandı**
- ~~BTK/kamu çıktı kanalı~~ — **tamamlandı** (yapılandırılabilir uç nokta; BTK/MASAK/USOM)
- ~~Çok kullanıcılı rol yönetimi~~ — **tamamlandı** (Sahip/Yönetici/Üye + `require_role`)
- ~~Canlı API'lere karşı entegrasyon testleri~~ — **tamamlandı** (`pytest -m integration`)
