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
    from app.modules.security_scan import module as _security  # noqa: F401
    from app.modules.brand_protection import module as _brand  # noqa: F401
    from app.modules.financial_crime import module as _financial  # noqa: F401
    from app.modules.competitor_intel import module as _competitor  # noqa: F401
    from app.modules.disinformation import module as _disinfo  # noqa: F401
    from app.modules.due_diligence import module as _dd  # noqa: F401
    from app.modules.ai_testing import module as _ai  # noqa: F401

    _loaded = True
