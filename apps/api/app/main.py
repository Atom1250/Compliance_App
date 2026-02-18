"""FastAPI application factory and app instance."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.api.app.api.routers.companies import router as companies_router
from apps.api.app.api.routers.documents import router as documents_router
from apps.api.app.api.routers.materiality import router as materiality_router
from apps.api.app.api.routers.retrieval import router as retrieval_router
from apps.api.app.api.routers.system import router as system_router
from apps.api.app.core.auth import validate_auth_configuration
from apps.api.app.core.config import get_settings
from apps.api.app.core.ops import validate_runtime_configuration


def _is_sensitive_path(path: str) -> bool:
    return (
        path == "/documents/upload"
        or path.endswith("/execute")
        or path.endswith("/evidence-pack")
    )


class RequestOpsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _is_rate_limited(self, *, tenant_id: str, path: str) -> bool:
        settings = get_settings()
        if not settings.request_rate_limit_enabled or not _is_sensitive_path(path):
            return False

        now = time.monotonic()
        key = (tenant_id, path)
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - settings.request_rate_limit_window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= settings.request_rate_limit_max_requests:
                return True
            bucket.append(now)
            return False

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        tenant_id = request.headers.get("X-Tenant-ID", "default")

        if self._is_rate_limited(tenant_id=tenant_id, path=request.url.path):
            response = JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded", "request_id": request_id},
            )
            response.headers["X-Request-ID"] = request_id
            return response

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    """Create FastAPI app with deterministic configuration wiring."""
    settings = get_settings()
    validate_auth_configuration(
        security_enabled=settings.security_enabled,
        auth_api_keys=settings.auth_api_keys,
        auth_tenant_keys=settings.auth_tenant_keys,
    )
    validate_runtime_configuration(settings)
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    allowed_origins = [
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestOpsMiddleware)
    app.include_router(system_router)
    app.include_router(companies_router)
    app.include_router(documents_router)
    app.include_router(materiality_router)
    app.include_router(retrieval_router)
    return app


app = create_app()
