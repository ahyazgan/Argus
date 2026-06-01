"""Modul soyut tabani ve global kayit defteri.

Argus'un genisleyebilirliginin kalbi: her modul (`modules/<ad>/module.py`) kendini
`register()` ile kayit defterine ekler. Cekirdek servisler (auth, kuyruk, Claude,
bildirim) tum modullerce paylasilir; moduller sadece kendi toplama/analiz mantigini ekler.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core_services.claude_engine.engine import TriageResult


@dataclass(frozen=True)
class ModuleMeta:
    key: str  # benzersiz anahtar, orn "darkweb"
    name: str  # Turkce gorunen ad
    description: str
    category: str  # gorseldeki renk grubu / kategori
    asset_types: list[str] = field(default_factory=list)  # izlenebilir varlik tipleri
    enabled: bool = True  # platformda canli mi (yoksa "yakinda")


@dataclass
class ScanResult:
    """Bir tarama sonucunda uretilen ham bulgu (analizden once)."""

    title: str
    raw_data: dict
    source: str
    asset_value: str


class ArgusModule(ABC):
    """Tum modullerin tabani."""

    meta: ModuleMeta

    @abstractmethod
    async def scan(self, monitor) -> list[ScanResult]:
        """Verilen monitor icin kaynaklari tarayip ham bulgulari dondurur."""
        raise NotImplementedError

    @abstractmethod
    def analyze(self, result: ScanResult, monitor) -> TriageResult:
        """Ham bir tarama sonucunu triyaj eder (severity + Turkce ozet/oneri).

        Genelde Claude motoruna modulun kendi sistem promptu ve heuristic'i ile delege edilir.
        """
        raise NotImplementedError


# --- Global kayit defteri ---
_REGISTRY: dict[str, ArgusModule] = {}


def register(module: ArgusModule) -> None:
    """Bir modulu kayit defterine ekler (module.py icinde cagrilir)."""
    _REGISTRY[module.meta.key] = module


def get_module(key: str) -> ArgusModule | None:
    return _REGISTRY.get(key)


def all_modules() -> list[ArgusModule]:
    return list(_REGISTRY.values())


def all_module_keys() -> list[str]:
    return list(_REGISTRY.keys())
