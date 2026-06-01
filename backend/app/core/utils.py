"""Kucuk yardimci fonksiyonlar."""
from __future__ import annotations

import re
import unicodedata


def slugify(value: str) -> str:
    """Turkce karakterleri sadelestirip URL dostu slug uretir."""
    value = value.replace("ı", "i").replace("İ", "i").replace("ş", "s").replace("Ş", "s")
    value = value.replace("ğ", "g").replace("Ğ", "g").replace("ü", "u").replace("Ü", "u")
    value = value.replace("ö", "o").replace("Ö", "o").replace("ç", "c").replace("Ç", "c")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "org"
