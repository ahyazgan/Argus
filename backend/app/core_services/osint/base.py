"""Ortak OSINT toplayici arayuzu - tum modullerin kaynak konnektorleri bunu uygular.

Her konnektor yasal/halka acik bir kaynagi sorgular ve ham kayitlar dondurur.
Modul, bu ham kayitlari Claude motoruyla triyaj edip Finding'e cevirir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Collector(ABC):
    """Bir veri kaynagini sorgulayan toplayici."""

    name: str

    @abstractmethod
    def collect(self, asset_type: str, asset_value: str) -> list[dict]:
        """Verilen varlik icin ham kayitlari dondurur (her biri bir dict)."""
        raise NotImplementedError
