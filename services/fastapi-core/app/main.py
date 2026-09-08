from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.authz import authz_client
from app.core.minio_client import ensure_buckets
from app.core.qdrant import ensure_collections
from app.core.rate_limit import client_key, rate_limiter
from app.routers import (
    analytics,
    api_keys,
    assets,
    audit,
    auth,
    brands,
    content,
    generations,
    health,
    invites,
    mcp,
    orchestrator,
    playbooks,
    usage,
)
from app.version import API_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_buckets()
    await ensure_collections()
    await authz_client.warm()
    yield


app = FastAPI(
    title="OpenGrow Core",
    version=API_VERSION,
    docs_url="/docs" if settings.OPENGROW_ENV != "prod" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Explicit list only (never reflect + credentials). Cookie-mode auth
    # transports the session via httpOnly cookies set by the node-gateway BFF
    # (SameSite=Strict), so credentialed cross-origin requests must be
    # allowed; lite mode stays Bearer-in-header and simply ignores cookies.
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],  # pagination total for browser clients
)


_RATE_LIMIT_EXEMPT = {"/health", "/ready", "/version"}


@app.middleware("http")
async def _rate_limit(request: Request, call_next):
    if not settings.RATE_LIMIT_ENABLED or request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path in _RATE_LIMIT_EXEMPT:
        return await call_next(request)
    allowed = await rate_limiter.allow(
        client_key(request), settings.RATE_LIMIT_PER_MINUTE, 60
    )
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": "60"},
        )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def _validation_handler(_request: Request, exc: RequestValidationError):
    """Normalize 422s so `detail` is always a human-readable string (clients
    read `detail`); the structured list stays available under `errors`."""
    errors = exc.errors()
    message = (
        "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', []) if p != 'body')}: {e.get('msg', '')}".strip(
                ": "
            )
            for e in errors
        )
        or "Validation error"
    )
    return JSONResponse(
        status_code=422,
        content={"detail": message, "errors": jsonable_encoder(errors)},
    )


app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(generations.router, prefix="/generations", tags=["generations"])
app.include_router(content.router, prefix="/content", tags=["content"])
app.include_router(brands.router, prefix="/brands", tags=["brands"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
app.include_router(usage.router, prefix="/usage", tags=["usage"])
app.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
app.include_router(orchestrator.router, prefix="/orchestrator", tags=["orchestrator"])
app.include_router(playbooks.router, prefix="/playbooks", tags=["playbooks"])
app.include_router(invites.router, prefix="/invites", tags=["invites"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])
