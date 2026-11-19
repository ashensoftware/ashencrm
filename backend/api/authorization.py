"""Clasificación de rutas y compuerta de acceso para /api.

Las rutas que no empiezan por /api (el frontend estático) no pasan por aquí.
Los permisos salen del rol ya verificado; no se aceptan del cliente.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.core.auth import AuthFailure, TokenAuthenticator

PUBLIC_ROUTES = {
    ("GET", "/api/livez"),
    ("GET", "/api/auth/config"),
}


class RateLimiter:
    """Ventana deslizante en memoria. Vale para un solo proceso."""

    def __init__(self, limit: int = 240, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        bucket = self._hits[key]
        cutoff = moment - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(moment)
        return True


def required_access(method: str, path: str) -> str | None:
    """None = pública. 'authenticated' = cualquier rol. 'role:admin' o un permiso."""
    normalized = path.split("?", 1)[0].rstrip("/") or "/"
    verb = method.upper()
    if (verb, normalized) in PUBLIC_ROUTES:
        return None
    if not normalized.startswith("/api"):
        return None
    if verb == "OPTIONS":
        return None
    if normalized.startswith("/api/admin"):
        return "role:admin"
    if normalized.endswith("/send-whatsapp"):
        return "outreach:send"
    if normalized.startswith("/api/approvals/outreach"):
        return "outreach:approve"
    if normalized.startswith("/api/approvals"):
        return "demos:approve"
    if "/pipeline-runs/" in normalized and normalized.endswith(("/pause", "/resume", "/cancel", "/retry-failed")):
        return "runs:cancel"
    if verb in {"POST", "PUT", "PATCH", "DELETE"}:
        return "campaigns:run"
    return "authenticated"


def _denied(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


class ApiAccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, authenticator: TokenAuthenticator, limiter: RateLimiter | None = None, audit=None):
        super().__init__(app)
        self.authenticator = authenticator
        self.limiter = limiter or RateLimiter()
        self.audit = audit

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api"):
            return await call_next(request)
        client = request.client.host if request.client else "local"
        if not self.limiter.allow(client):
            return _denied(429, "Demasiadas solicitudes")
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > 1_000_000:
            return _denied(413, "El cuerpo de la solicitud supera el límite")
        access = required_access(request.method, path)
        principal = None
        if access is not None:
            try:
                principal = self.authenticator.authenticate(request.headers.get("authorization"))
            except AuthFailure as exc:
                return _denied(exc.status_code, exc.detail)
            request.state.principal = principal
            if access == "role:admin" and principal.role != "admin":
                return _denied(403, "Se requiere rol admin")
            if access not in {"authenticated", "role:admin"} and access not in principal.permissions:
                return _denied(403, f"Permiso insuficiente: {access}")
        response = await call_next(request)
        if self.audit and principal is not None and request.method.upper() != "GET":
            self.audit(
                subject=principal.subject,
                role=principal.role,
                method=request.method.upper(),
                path=path.split("?", 1)[0],
                status_code=response.status_code,
            )
        return response
