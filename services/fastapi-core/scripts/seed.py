"""Seed one demo tenant + one demo user + OpenFGA membership."""

import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.core.auth import hash_password
from app.core.authz import authz_client
from app.database import SessionLocal
from app.models.tenant import Tenant
from app.models.user import User

DEMO_TENANT_SLUG = "demo"
DEMO_TENANT_NAME = "Demo Tenant"
DEMO_EMAIL = "demo@opengrow.dev"
DEMO_PASSWORD = "123456"


async def seed() -> None:
    async with SessionLocal() as db:
        row = await db.execute(select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG))
        tenant = row.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(id=uuid4(), slug=DEMO_TENANT_SLUG, name=DEMO_TENANT_NAME)
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            print(f"Created tenant: {tenant.id}")
        else:
            print(f"Tenant exists: {tenant.id}")

        row = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        user = row.scalar_one_or_none()
        if not user:
            user = User(
                id=uuid4(),
                tenant_id=tenant.id,
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name="Demo User",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Created user: {user.id} ({user.email})")
        else:
            print(f"User exists: {user.id}")

    # OpenFGA relations (idempotent write)
    try:
        await authz_client.write_membership(str(user.id), str(tenant.id), role="admin")
        await authz_client.write_membership(str(user.id), str(tenant.id), role="member")
        print("OpenFGA memberships written")
    except Exception as e:
        print(f"OpenFGA seed skipped (probably already present): {e}")

    print("\n== Demo credentials ==")
    print(f"  email:    {DEMO_EMAIL}")
    print(f"  password: {DEMO_PASSWORD}")
    print(f"  tenant:   {tenant.slug} ({tenant.id})")


if __name__ == "__main__":
    asyncio.run(seed())
