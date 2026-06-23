"""Yasadisi site tespiti modulu - ArgusModule uygulamasi ve kayit."""
from __future__ import annotations

from app.core.config import settings
from app.core_services.claude_engine.engine import TriageResult
from app.modules.base import ArgusModule, ModuleMeta, ScanResult, register
from app.modules.catalog import CATALOG_BY_KEY
from app.modules.illegal_site.analyzer import analyze as analyze_illegal
from app.modules.illegal_site.collectors import get_collectors
from app.modules.illegal_site.enrichment import enrich_domain


class IllegalSiteModule(ArgusModule):
    meta: ModuleMeta = CATALOG_BY_KEY["illegal_site"]

    async def scan(self, monitor) -> list[ScanResult]:
        results: list[ScanResult] = []
        live = getattr(settings, "illegal_live_enrich", False)
        for collector in get_collectors():
            for raw in collector.collect(monitor.asset_type, monitor.asset_value):
                domain = raw.get("candidate_domain")
                # Canli zenginlestirme acik ve gercek bir aday alan adi varsa, kanit topla
                # (HTTP icerik + RDAP WHOIS yasi + DNS). Bayrak kapaliyken ag cagrisi yapilmaz.
                if live and domain:
                    raw = {**raw, **enrich_domain(domain)}
                results.append(
                    ScanResult(
                        title=f"{domain or monitor.asset_value} - supheli site",
                        raw_data=raw,
                        source=raw.get("source", collector.name),
                        asset_value=monitor.asset_value,
                    )
                )
        return results

    def analyze(self, result: ScanResult, monitor) -> TriageResult:
        return analyze_illegal(result, monitor.asset_type)


# Modulu global kayit defterine ekle (load_modules() bu dosyayi import eder)
register(IllegalSiteModule())
