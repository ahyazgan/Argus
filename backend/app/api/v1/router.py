"""v1 API router toplayicisi - alt routerlar burada birlestirilir."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    billing,
    findings,
    health,
    modules,
    monitors,
    reports,
    settings as settings_api,
    team,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(modules.router, prefix="/modules", tags=["modules"])
# Genel monitor/tarama uclari - tum moduller icin: /m/{module_key}/...
api_router.include_router(monitors.router, prefix="/m", tags=["monitors"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(settings_api.router, prefix="/settings", tags=["settings"])
api_router.include_router(team.router, prefix="/team", tags=["team"])
