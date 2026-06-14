"""CSV disa aktarim (cikti katmani) - bulgulari elektronik tablo dostu CSV'ye cevirir.

Saf fonksiyon: DB/IO bagimsiz, kolayca birim-testlenir. Excel'in Turkce/UTF-8
karakterleri dogru gostermesi icin cagiran taraf BOM ekleyebilir.
"""
from __future__ import annotations

import csv
import io
from typing import Iterable

_COLUMNS = [
    ("detected_at", "Tespit"),
    ("severity", "Onem"),
    ("status", "Durum"),
    ("module_key", "Modul"),
    ("title", "Baslik"),
    ("asset_value", "Varlik"),
    ("source", "Kaynak"),
    ("seen_count", "Gorulme"),
    ("summary", "Ozet"),
    ("recommendation", "Oneri"),
]


def _cell(value) -> str:
    if value is None:
        return ""
    # datetime -> ISO; digerleri str
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return str(value)


def findings_to_csv(findings: Iterable) -> str:
    """Bulgu nesnelerini (ORM ya da benzer attribute'lara sahip) CSV metnine cevirir."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([header for _, header in _COLUMNS])
    for f in findings:
        writer.writerow([_cell(getattr(f, attr, None)) for attr, _ in _COLUMNS])
    return buf.getvalue()
