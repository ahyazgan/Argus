"""Celery worker giris noktasi.

Calistirma:  celery -A app.worker.celery_app worker --loglevel=info
(Windows yerelde:  ... --pool=solo)
"""
from __future__ import annotations

from app.core_services.queue.celery_app import celery_app  # noqa: F401

# Genel tarama gorevinin kayit olmasi icin ice aktar
import app.core_services.queue.scan_tasks  # noqa: E402, F401

# Modullerin kayit defterine yuklenmesi
from app.modules import load_modules  # noqa: E402

load_modules()
