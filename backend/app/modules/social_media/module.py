"""Sosyal medya hesap taklidi modulu - ArgusModule uygulamasi ve kayit."""
from __future__ import annotations

from app.core_services.claude_engine.engine import TriageResult
from app.modules.base import ArgusModule, ModuleMeta, ScanResult, register
from app.modules.catalog import CATALOG_BY_KEY
from app.modules.social_media.analyzer import analyze as analyze_social
from app.modules.social_media.collectors import get_collectors


class SocialMediaModule(ArgusModule):
    meta: ModuleMeta = CATALOG_BY_KEY["social_media"]

    async def scan(self, monitor) -> list[ScanResult]:
        results: list[ScanResult] = []
        for collector in get_collectors():
            for raw in collector.collect(monitor.asset_type, monitor.asset_value):
                results.append(
                    ScanResult(
                        title=f"{raw.get('handle', monitor.asset_value)} - olasi taklit hesap",
                        raw_data=raw,
                        source=raw.get("source", collector.name),
                        asset_value=monitor.asset_value,
                    )
                )
        return results

    def analyze(self, result: ScanResult, monitor) -> TriageResult:
        return analyze_social(result, monitor.asset_type)


# Modulu global kayit defterine ekle (load_modules() bu dosyayi import eder)
register(SocialMediaModule())
