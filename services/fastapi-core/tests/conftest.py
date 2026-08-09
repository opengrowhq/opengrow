"""Integration-test harness.

Spins up an isolated `opengrow_test` database on the same Postgres, creates the
schema from the SQLAlchemy metadata, and drives the real FastAPI app in-process
via httpx ASGITransport with `get_db` overridden to point at the test DB.

Runs in lite mode (DEPLOYMENT_MODE=lite in the container), so authz is the stub
and tenant isolation is enforced purely by the SQL `tenant_id` filters — which
is exactly what these tests exercise.
"""

from __future__ import annotations

import asyncio
import uuid

import psycopg2
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.core.auth import hash_password, issue_access
from app.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User

TEST_DB = "opengrow_test"


def _test_dsn() -> str:
    return (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{TEST_DB}"
    )


def _admin_conn():
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname="postgres",
    )
    conn.autocommit = True
    return conn


@pytest.fixture(scope="session", autouse=True)
def _setup_test_db():
    # (Re)create the test database (sync — avoids event-loop scoping issues).
    conn = _admin_conn()
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    cur.execute(f"CREATE DATABASE {TEST_DB}")
    cur.close()
    conn.close()

    async def _create_schema():
        engine = create_async_engine(_test_dsn())
        async with engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create_schema())
    yield
    conn = _admin_conn()
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    cur.close()
    conn.close()


@pytest_asyncio.fixture
async def engine(_setup_test_db):
    eng = create_async_engine(_test_dsn())
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine):
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def no_celery(monkeypatch):
    """Neutralize Celery dispatch so generation/run endpoints don't enqueue a
    real task (the worker points at a different DB in tests)."""
    from types import SimpleNamespace

    from app.workers import tasks

    stub = lambda *a, **k: SimpleNamespace(id="test-task")  # noqa: E731
    monkeypatch.setattr(tasks.run_generation, "delay", stub)
    monkeypatch.setattr(tasks.run_orchestrator, "delay", stub)


def _test_sync_dsn() -> str:
    return (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{TEST_DB}"
    )


@pytest.fixture
def sync_db(_setup_test_db):
    """A synchronous Session on the test DB — for exercising Celery-side
    (sync) logic like the orchestrator pipeline."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(_test_sync_dsn())
    SessionSync = sessionmaker(engine, expire_on_commit=False)
    with SessionSync() as session:
        yield session
    engine.dispose()


@pytest_asyncio.fixture
async def tenant_factory(db):
    """Create a fresh tenant + user; returns dict with token + auth headers.

    Each call uses unique slug/email so tests don't collide across the shared
    schema (all queries are tenant-scoped, so accumulated data is invisible
    across tenants)."""

    async def _make(password: str = "pw-123456"):
        suffix = uuid.uuid4().hex[:10]
        tenant = Tenant(id=uuid.uuid4(), slug=f"t-{suffix}", name=f"Tenant {suffix}")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

        email = f"user-{suffix}@example.com"
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            email=email,
            password_hash=hash_password(password),
            display_name="Test User",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        token = issue_access(str(user.id), str(tenant.id))
        return {
            "tenant": tenant,
            "user": user,
            "email": email,
            "password": password,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    return _make
