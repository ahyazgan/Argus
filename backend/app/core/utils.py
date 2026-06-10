"""Kucuk yardimci fonksiyonlar."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

# Onem siralamasi (dusuk -> yuksek). Bildirim esigi ve karsilastirmalar icin.
SEVERITY_ORDER: tuple[str, ...] = ("info", "low", "medium", "high", "critical")


def slugify(value: str) -> str:
    """Turkce karakterleri sadelestirip URL dostu slug uretir."""
    value = value.replace("ı", "i").replace("İ", "i").replace("ş", "s").replace("Ş", "s")
    value = value.replace("ğ", "g").replace("Ğ", "g").replace("ü", "u").replace("Ü", "u")
    value = value.replace("ö", "o").replace("Ö", "o").replace("ç", "c").replace("Ç", "c")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "org"


def severity_at_least(severity: str, threshold: str) -> bool:
    """severity, threshold seviyesinde veya uzerinde mi? Bilinmeyen deger -> True (bildir)."""
    try:
        return SEVERITY_ORDER.index(severity) >= SEVERITY_ORDER.index(threshold)
    except ValueError:
        return True


def finding_fingerprint(module_key: str, monitor_id, raw_data: dict) -> str:
    """Bir bulgu icin deterministik parmak izi.

    Ayni monitor + ayni ham veri => ayni parmak izi. Boylece periyodik taramalar ayni
    bulguyu cogaltmaz (upsert: varsa guncelle, yoksa olustur).
    """
    canonical = json.dumps(raw_data, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(f"{module_key}|{monitor_id}|{canonical}".encode()).hexdigest()
    return digest[:32]
