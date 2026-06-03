"""HTTP middleware'leri: guvenlik basliklari + basit (in-memory) rate limiting.

Rate limiter tek surec icindir (in-memory); cok-instance uretimde Redis tabanli bir
limiter (orn slowapi) tercih edilmelidir. Burada amac, brute-force'a karsi auth
uclarini korumak ve makul bir varsayilan sunmaktir.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "0",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for k, v in _SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        return response


def allow_request(history: deque[float], now: float, limit: int, window: float) -> bool:
    """Saf sliding-window karari: pencere icindeki istek sayisi limit altindaysa True.

    Izin verilirse `now` gecmise eklenir. (history yerinde guncellenir.)
    """
    while history and history[0] <= now - window:
        history.popleft()
    if len(history) >= limit:
        return False
    history.append(now)
    return True


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    """Yalnizca auth (login/register/accept-invite) uclarini IP basina sinirlar."""

    def __init__(self, app, limit_per_minute: int, protected_prefixes: tuple[str, ...]):
        super().__init__(app)
        self.limit = limit_per_minute
        self.window = 60.0
        self.prefixes = protected_prefixes
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if request.method == "POST" and any(path.startswith(p) for p in self.prefixes):
            ip = request.client.host if request.client else "unknown"
            if not allow_request(self._hits[ip], time.monotonic(), self.limit, self.window):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Cok fazla deneme. Lutfen biraz sonra tekrar deneyin."},
                )
        return await call_next(request)
