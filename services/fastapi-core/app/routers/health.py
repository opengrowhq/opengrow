import asyncio
import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.version import API_VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "mode": settings.DEPLOYMENT_MODE,
    }


@router.get("/version")
async def version():
    """Service + API version, for clients to feature-detect against."""
    return {
        "service": settings.SERVICE_NAME,
        "version": API_VERSION,
        "mode": settings.DEPLOYMENT_MODE,
        "env": settings.OPENGROW_ENV,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def ready():
    """Deep readiness — DB + MinIO always; OpenFGA/LiteLLM/Qdrant only in production."""
    results = {}
    ok = True

    try:
        async with engine.connect() as c:
            await c.execute(text("SELECT 1"))
        results["postgres"] = "ok"
    except Exception as e:
        results["postgres"] = f"err:{e.__class__.__name__}"
        ok = False

    async def _http(name: str, url: str):
        nonlocal ok
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(url)
                r.raise_for_status()
            results[name] = "ok"
        except Exception as e:
            results[name] = f"err:{e.__class__.__name__}"
            ok = False

    checks = [
        _http(
            "minio",
            f"http://{settings.MINIO_HOST}:{settings.MINIO_PORT}/minio/health/live",
        ),
    ]
    if not settings.is_lite:
        checks.extend(
            [
                _http(
                    "qdrant",
                    f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/readyz",
                ),
                _http("openfga", f"{settings.OPENFGA_API_URL}/healthz"),
                _http("litellm", f"{settings.LITELLM_URL}/health/liveliness"),
            ]
        )
    await asyncio.gather(*checks)

    body = {"ready": ok, "mode": settings.DEPLOYMENT_MODE, "checks": results}
    if not ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body
        )
    return body
