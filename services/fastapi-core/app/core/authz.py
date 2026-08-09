"""OpenFGA client (production) + stub client (lite mode).

Model (see infra/openfga/model.fga):

    user
    tenant [member, admin]
    asset [tenant, owner, reader = member from tenant, writer = admin from tenant]
    generation [tenant, owner, reader = member from tenant]

Every mutation/read of a tenant-owned resource MUST call authz_client.check(...).

Lite mode: a stub client returns `allowed=True` for every check. Tenant isolation
is still enforced at the SQL layer via `tenant_id` filters — the stub only removes
the ReBAC layer, appropriate for single-tenant personal deployments.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Protocol

from app.config import settings

log = logging.getLogger("authz")


def _scrub(value: object) -> str:
    """Strip CR/LF so user-controlled values can't forge log lines (log injection)."""
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


class AuthZClientProtocol(Protocol):
    async def warm(self) -> None: ...
    async def check(self, user_id: str, relation: str, object_id: str) -> bool: ...
    async def write_membership(
        self, user_id: str, tenant_id: str, role: str = "member"
    ) -> None: ...
    async def bind_resource_to_tenant(
        self, object_type: str, object_id: str, tenant_id: str, owner_user_id: str
    ) -> None: ...


class _StubAuthZClient:
    """Lite mode: everything allowed. Tenant isolation still enforced in SQL."""

    async def warm(self) -> None:
        log.info("authz: lite-mode stub (all checks allowed)")

    async def check(self, user_id: str, relation: str, object_id: str) -> bool:
        return True

    async def write_membership(
        self, user_id: str, tenant_id: str, role: str = "member"
    ) -> None:
        return None

    async def bind_resource_to_tenant(
        self, object_type: str, object_id: str, tenant_id: str, owner_user_id: str
    ) -> None:
        return None


class _OpenFGAClient:
    def __init__(self) -> None:
        self._client = None  # type: ignore[assignment]
        self._lock = asyncio.Lock()

    async def _get(self):
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    from openfga_sdk import OpenFgaClient
                    from openfga_sdk.client import ClientConfiguration

                    self._client = OpenFgaClient(
                        ClientConfiguration(
                            api_url=settings.OPENFGA_API_URL,
                            store_id=settings.OPENFGA_STORE_ID,
                            authorization_model_id=settings.OPENFGA_MODEL_ID,
                        )
                    )
        return self._client

    async def warm(self) -> None:
        try:
            await self._get()
        except Exception as e:
            log.error("OpenFGA warm failed: %s", e)

    async def check(self, user_id: str, relation: str, object_id: str) -> bool:
        from openfga_sdk.client.models import ClientCheckRequest

        client = await self._get()
        try:
            resp = await client.check(
                body=ClientCheckRequest(
                    user=f"user:{user_id}",
                    relation=relation,
                    object=object_id,
                )
            )
            return bool(resp.allowed)
        except Exception as e:
            log.error(
                "authz.check(%s,%s,%s) failed: %s",
                _scrub(user_id),
                _scrub(relation),
                _scrub(object_id),
                e,
            )
            return False

    async def write_membership(
        self, user_id: str, tenant_id: str, role: str = "member"
    ) -> None:
        from openfga_sdk.client.models import ClientTuple, ClientWriteRequest

        client = await self._get()
        await client.write(
            ClientWriteRequest(
                writes=[
                    ClientTuple(
                        user=f"user:{user_id}",
                        relation=role,
                        object=f"tenant:{tenant_id}",
                    )
                ]
            )
        )

    async def bind_resource_to_tenant(
        self, object_type: str, object_id: str, tenant_id: str, owner_user_id: str
    ) -> None:
        from openfga_sdk.client.models import ClientTuple, ClientWriteRequest

        client = await self._get()
        await client.write(
            ClientWriteRequest(
                writes=[
                    ClientTuple(
                        user=f"tenant:{tenant_id}",
                        relation="tenant",
                        object=f"{object_type}:{object_id}",
                    ),
                    ClientTuple(
                        user=f"user:{owner_user_id}",
                        relation="owner",
                        object=f"{object_type}:{object_id}",
                    ),
                ]
            )
        )


authz_client: AuthZClientProtocol = (
    _StubAuthZClient() if settings.is_lite else _OpenFGAClient()
)
