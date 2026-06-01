"""Modul paketi - canli modulleri kayit defterine yukler."""
from __future__ import annotations

_loaded = False


def load_modules() -> None:
    """Calisan modulleri ice aktararak kendilerini register etmelerini saglar.

    Uygulama acilisinda (lifespan) bir kez cagrilir. Yeni canli modul eklerken
    buraya bir import satiri eklenir.
    """
    global _loaded
    if _loaded:
        return
    # Canli moduller (catalog'da enabled=True olanlar):
    from app.modules.darkweb import module as _darkweb  # noqa: F401
    from app.modules.illegal_site import module as _illegal  # noqa: F401

    _loaded = True
