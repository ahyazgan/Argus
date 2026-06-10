"""Rakip istihbarat modulu - ArgusModule uygulamasi ve kayit."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult
from app.modules.base import ArgusModule, ModuleMeta, ScanResult, register
from app.modules.catalog import CATALOG_BY_KEY
from app.modules.competitor_intel.analyzer import analyze as analyze_competitor
from app.modules.competitor_intel.collectors import get_collectors


class CompetitorIntelModule(ArgusModule):
    meta: ModuleMeta = CATALOG_BY_KEY["competitor_intel"]

    async def scan(self, monitor) -> list[ScanResult]:
        results: list[ScanResult] = []
        for collector in get_collectors():
            for raw in collector.collect(monitor.asset_type, monitor.asset_value):
                results.append(
                    ScanResult(
                        title=f"{raw.get('competitor', monitor.asset_value)} - rakip degisikligi",
                        raw_data=raw,
                        source=raw.get("source", collector.name),
                        asset_value=monitor.asset_value,
                    )
                )
        return results

    def analyze(self, result: ScanResult, monitor) -> TriageResult:
        return analyze_competitor(result, monitor.asset_type)


# Modulu global kayit defterine ekle (load_modules() bu dosyayi import eder)
register(CompetitorIntelModule())
