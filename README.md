# Argus Intelligence

**Tek platform — sonsuz modül — bir abonelik.** OSINT & tehdit istihbaratı SaaS platformu.

Ortak bir çekirdeği (auth, görev kuyruğu, Claude AI motoru, bildirim, ödeme) paylaşan,
müşteriye göre açılıp kapanan modüllerden ve tek tip bir çıktı katmanından oluşur.

Bu repo, mimariyi uçtan uca kanıtlayan bir **dikey dilim (MVP)** içerir:
ortak çekirdek + **2 canlı modül** (Dark web izleme, Yasadışı site tespiti) +
dashboard + PDF/REST çıktısı. Modüller ortak, modülden-bağımsız bir tarama
motorunu ve genel API'yi (`/api/v1/m/{module_key}/...`) paylaşır.

---

## Mimari

```
Ortak çekirdek (core_services/)        Modüller (modules/)            Çıktı (outputs/ + api/)
├─ OSINT toplayıcı (osint/)            ├─ base.py  (Module ABC +      ├─ Dashboard (Next.js)
├─ Claude AI motoru (claude_engine/)   │           kayıt defteri)     ├─ PDF rapor (WeasyPrint)
├─ Async kuyruk (queue/ — Celery)      ├─ catalog.py (9 modül)        ├─ REST API (FastAPI)
│   + genel tarama görevi              ├─ darkweb/        ← CANLI     └─ Webhook / Slack
├─ Bildirim (notifications/)           ├─ illegal_site/   ← CANLI
└─ Multi-tenant auth (core/)           └─ (diğer 7 "yakında")
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

> Tablolar açılışta otomatik oluşturulur (`create_all`). Üretim için Alembic hazırdır:
> `docker compose exec backend alembic revision --autogenerate -m "init" && alembic upgrade head`.

---

## Demo akışı (uçtan uca)

1. http://localhost:3000 → **Kayıt ol** (kurum adı + e-posta + parola). Otomatik olarak
   bir Organization + owner kullanıcı + Starter abonelik oluşur.
2. **Modüller** sayfasında **Dark web izleme**’yi **Aç** (Starter planı 2 modüle izin verir).
3. **Dark web izleme** sayfasında bir monitör ekleyin (örn. tip `domain`, değer `ornek.com`).
4. Monitörde **Tara**’ya basın → Celery görevi arka planda çalışır.
5. Demo konnektör + Claude triyajı bulgular üretir (önem + Türkçe özet + öneri).
6. **PDF rapor indir** → WeasyPrint ile Türkçe rapor.
7. **Ayarlar**’da webhook/Slack URL’i tanımlayın → yeni bulguda bildirim gönderilir.
8. **Abonelik**’te plan limitini test edin (limit aşımı reddedilir).

> Aynı akış **Yasadışı site tespiti** modülü için de geçerlidir: Modüller’den açın, sol
> menüden modüle girin, bir marka/anahtar kelime (örn. `markam`) ekleyip tarayın → kumar/
> dolandırıcılık şüpheli siteleri + BTK ihbar önerisi içeren bulgular üretilir. Yeni modüller
> sol menüde otomatik belirir.

---

## Testler

```bash
docker compose exec backend pytest
```

DB gerektirmeyen çekirdek birim testleri (`backend/tests/test_core.py`):
slugify, parola hash, plan limitleri, modül katalogu, sezgisel triyaj, demo konnektör.

---

## Notlar / sınırlar

- **Etik/yasal:** Dark web modülü **savunma amaçlıdır** — yalnızca müşterinin *kendi*
  varlıkları için, yasal/halka açık kaynaklardan sızıntı izler. Yasadışı pazar yeri
  tarayıcısı / Tor crawler içermez.
- **Demo konnektörü** anahtarsız çalışır (deterministik örnek). Gerçek sızıntı feed’leri
  (HIBP vb.) takılabilir `Collector` olarak `modules/darkweb/collectors.py` içine eklenir.
- **Stripe** şu an stub (`STRIPE_ENABLED=false`). Plan değiştirme limit dayatmasını gösterir.
- **Çıktı kanalları:** Dashboard, PDF, REST, Webhook/Slack canlı; Jira/GitHub ve BTK/kamu API
  arayüzde "yakında" — sonraki dilim.
- **Windows yerel (Docker'sız) çalıştırma:** Celery için `--pool=solo`, WeasyPrint için GTK
  bağımlılıkları gerekir; bu yüzden birincil yol Docker'dır.

---

## Yol haritası (sonraki dilimler)

- Diğer 7 modül (Güvenlik tarama, Marka koruma, Due diligence, …) — aynı çekirdeğe takılır
- Gerçek Stripe webhook'ları + faturalandırma
- Jira/GitHub ticket ve BTK/kamu API çıktı kanalları
- Zamanlanmış (periyodik) taramalar (Celery beat)
- Gerçek dark web / sızıntı feed entegrasyonları
