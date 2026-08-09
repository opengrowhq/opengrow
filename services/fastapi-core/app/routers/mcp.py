from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.mcp import handle_jsonrpc
from app.database import get_db
from app.models.user import User

router = APIRouter()


@router.post("")
async def mcp_endpoint(
    payload: dict,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """MCP JSON-RPC endpoint. Auth via X-API-Key (or Bearer). One request per
    call (no batching); notifications get a 202 with no body."""
    result = await handle_jsonrpc(payload, db, current)
    if result is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return result
