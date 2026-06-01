"""(Kullanim disi) Dark web'e ozel tarama gorevi.

Tarama artik modulden bagimsiz genel gorevle yapilir:
    app.core_services.queue.scan_tasks.run_module_scan

Bu dosya geriye donuk uyumluluk/yer tutucu olarak birakilmistir.
"""
from __future__ import annotations

from app.core_services.queue.scan_tasks import run_module_scan  # noqa: F401
