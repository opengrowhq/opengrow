"""JWT auth. Secret pulled from Infisical, never logged."""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.api_keys import hash_key
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
# auto_error=False so a request may authenticate with X-API-Key instead of Bearer.
_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_password(pw: str) -> str:
    return _pwd.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    return _pwd.verify(pw, hashed)


def _issue(sub: str, tenant_id: str, ttl_minutes: int, kind: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "tid": tenant_id,
        "kind": kind,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def issue_access(user_id: str, tenant_id: str) -> str:
    return _issue(user_id, tenant_id, settings.JWT_ACCESS_MINUTES, "access")


def issue_refresh(user_id: str, tenant_id: str) -> str:
    return _issue(user_id, tenant_id, settings.JWT_REFRESH_DAYS * 24 * 60, "refresh")


async def _user_from_api_key(db: AsyncSession, raw_key: str) -> User | None:
    row = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == hash_key(raw_key),
            ApiKey.is_active.is_(True),
            ApiKey.is_deleted.is_(False),
        )
    )
    key = row.scalar_one_or_none()
    if not key:
        return None
    user = await db.get(User, key.user_id)
    if not user or not user.is_active or user.tenant_id != key.tenant_id:
        return None
    key.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return user


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(_oauth2)] = None,
    api_key: Annotated[str | None, Depends(_api_key_header)] = None,
) -> User:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1) API key (headless clients).
    if api_key:
        user = await _user_from_api_key(db, api_key)
        if user:
            return user
        raise creds_exc

    # 2) Bearer JWT (interactive clients).
    if not token:
        raise creds_exc
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("kind") != "access":
            raise creds_exc
        user_id = payload.get("sub")
        tenant_id = payload.get("tid")
        if not user_id or not tenant_id:
            raise creds_exc
    except jwt.PyJWTError:
        raise creds_exc

    row = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = row.scalar_one_or_none()
    if not user or not user.is_active:
        raise creds_exc
    if str(user.tenant_id) != tenant_id:
        raise creds_exc
    return user
