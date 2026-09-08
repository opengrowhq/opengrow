from typing import Annotated
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.auth import get_current_user
from app.core.authz import authz_client
from app.core.article_metadata import article_content_metadata
from app.core.credential_crypto import (
    CredentialCryptoError,
    decrypt_secret,
    encrypt_secret,
)
from app.core.pagination import Page, paginate, pagination
from app.core.publishers import (
    KNOWN_CHANNELS,
    PublisherError,
    get_adapter,
    is_implemented,
)
from app.core.audit import record_audit_event
from app.core.usage import record_usage
from app.core.github_publisher import (
    GitHubPublishError,
    get_pull_request_status,
    publish_markdown,
    validate_token,
)
from app.database import get_db
from app.models.content_piece import ContentPiece, ContentStatus
from app.models.generation import Generation, GenerationStatus
from app.models.github_credential import GitHubCredential
from app.models.publication import Publication, PublicationChannel, PublicationStatus
from app.models.user import User
from app.schemas.content_piece import (
    ContentPieceCreate,
    ContentPieceFromGeneration,
    ContentPieceOut,
    ContentPieceTransition,
    ContentPieceUpdate,
    ScheduledPublish,
)
from app.schemas.publication import (
    GitHubCredentialOut,
    GitHubCredentialUpsert,
    GitHubPublishConfigOut,
    PublicationOut,
    PublishChannelOut,
    PublishGitHubRequest,
    PublishRequest,
)

router = APIRouter()

# Allowed editorial lifecycle transitions.
_TRANSITIONS: dict[ContentStatus, set[ContentStatus]] = {
    ContentStatus.DRAFT: {ContentStatus.IN_REVIEW, ContentStatus.ARCHIVED},
    ContentStatus.IN_REVIEW: {
        ContentStatus.APPROVED,
        ContentStatus.DRAFT,
        ContentStatus.ARCHIVED,
    },
    ContentStatus.APPROVED: {
        ContentStatus.PUBLISHED,
        ContentStatus.DRAFT,
        ContentStatus.ARCHIVED,
    },
    ContentStatus.PUBLISHED: {ContentStatus.ARCHIVED},
    ContentStatus.ARCHIVED: {ContentStatus.DRAFT},
}
_EDITABLE = {ContentStatus.DRAFT, ContentStatus.IN_REVIEW}


def _out(cp: ContentPiece) -> ContentPieceOut:
    metadata = cp.metadata_json or {}
    scheduled = metadata.get("scheduled_publish")
    return ContentPieceOut(
        id=str(cp.id),
        title=cp.title,
        body=cp.body,
        format=cp.format,
        status=cp.status.value,
        source_generation_id=(
            str(cp.source_generation_id) if cp.source_generation_id else None
        ),
        next_action=metadata.get("next_action"),
        due_at=metadata.get("due_at"),
        scheduled_publish=ScheduledPublish(**scheduled) if scheduled else None,
        created_at=cp.created_at,
        updated_at=cp.updated_at,
    )


def _pub_out(p: Publication) -> PublicationOut:
    return PublicationOut(
        id=str(p.id),
        content_piece_id=str(p.content_piece_id),
        channel=p.channel.value,
        status=p.status.value,
        url=p.url,
        external_ref=p.external_ref,
        error_message=p.error_message,
        target=p.target,
        created_at=p.created_at,
    )


def _slugify(value: str) -> str:
    out = []
    for ch in (value or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "post"


def _render_markdown(cp: ContentPiece) -> str:
    """Content as a Markdown document with publishable YAML frontmatter.

    Blog posts get the fields a static-site generator expects; internal
    bookkeeping (UUID, editorial status, format tag) is deliberately omitted so
    the published file is usable as-is.
    """

    def esc(v: str) -> str:
        return str(v).replace("\\", "\\\\").replace('"', '\\"')

    article = ((cp.metadata_json or {}).get("article")) or {}
    date = cp.created_at.date().isoformat()
    lines = ["---", f'title: "{esc(cp.title)}"']

    if (cp.format or "") == "blog_post":
        slug = _slugify(article.get("slug") or cp.title)
        description = article.get("description") or ""
        tags = article.get("tags") or []
        published = cp.status in (ContentStatus.APPROVED, ContentStatus.PUBLISHED)
        lines += [
            f"slug: {slug}",
            f"date: {date}",
            f'description: "{esc(description)}"',
            "tags: [" + ", ".join(f'"{esc(t)}"' for t in tags) + "]",
            f"draft: {'false' if published else 'true'}",
        ]
    else:
        lines.append(f"date: {date}")

    lines += ["---", "", ""]
    return "\n".join(lines) + (cp.body or "")


def _content_metadata(
    current: dict | None,
    *,
    set_next_action: bool = False,
    next_action: str | None = None,
    set_due_at: bool = False,
    due_at=None,
    set_scheduled_publish: bool = False,
    scheduled_publish=None,
) -> dict | None:
    metadata = dict(current or {})
    if set_next_action:
        if next_action:
            metadata["next_action"] = next_action
        else:
            metadata.pop("next_action", None)
    if set_due_at:
        if due_at:
            metadata["due_at"] = (
                due_at.isoformat() if isinstance(due_at, datetime) else due_at
            )
        else:
            metadata.pop("due_at", None)
    if set_scheduled_publish:
        if scheduled_publish:
            metadata["scheduled_publish"] = scheduled_publish.model_dump()
        else:
            metadata.pop("scheduled_publish", None)
    return metadata or None


def _publication_pr_number(pub: Publication) -> int | None:
    target = pub.target or {}
    value = target.get("pr_number")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if pub.external_ref:
        prefix = "PR #"
        if pub.external_ref.startswith(prefix):
            raw = pub.external_ref[len(prefix) :].split(" ", 1)[0]
            if raw.isdigit():
                return int(raw)
    return None


async def _load(db: AsyncSession, tenant_id: UUID, cp_id: UUID) -> ContentPiece:
    row = await db.execute(
        select(ContentPiece).where(
            ContentPiece.id == cp_id,
            ContentPiece.tenant_id == tenant_id,
            ContentPiece.is_deleted.is_(False),
        )
    )
    cp = row.scalar_one_or_none()
    if not cp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content piece not found")
    return cp


async def _assert_tenant_reader(current: User) -> None:
    if not await authz_client.check(
        str(current.id), "reader", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this tenant")


async def _assert_tenant_writer(current: User) -> None:
    if not await authz_client.check(
        str(current.id), "writer", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this tenant")


async def _load_github_credential(
    db: AsyncSession, tenant_id: UUID
) -> GitHubCredential | None:
    row = await db.execute(
        select(GitHubCredential)
        .where(
            GitHubCredential.tenant_id == tenant_id,
            GitHubCredential.is_deleted.is_(False),
        )
        .order_by(GitHubCredential.updated_at.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _resolve_github_token(
    db: AsyncSession, tenant_id: UUID
) -> tuple[str | None, GitHubCredential | None, str | None]:
    credential = await _load_github_credential(db, tenant_id)
    if credential:
        try:
            return decrypt_secret(credential.token_encrypted), credential, "tenant"
        except CredentialCryptoError as e:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Stored GitHub credential is unusable: {e}",
            ) from e
    settings = get_settings()
    if settings.GITHUB_TOKEN:
        return settings.GITHUB_TOKEN, None, "env"
    return None, None, None


@router.post("", response_model=ContentPieceOut, status_code=status.HTTP_201_CREATED)
async def create_content(
    payload: ContentPieceCreate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(
        str(current.id), "writer", f"tenant:{current.tenant_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this tenant")

    src_id = None
    if payload.source_generation_id:
        try:
            src_id = UUID(payload.source_generation_id)
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Invalid source_generation_id"
            )
        if not await authz_client.check(
            str(current.id), "reader", f"generation:{src_id}"
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Not permitted to reference this generation",
            )
        row = await db.execute(
            select(Generation).where(
                Generation.id == src_id,
                Generation.tenant_id == current.tenant_id,
                Generation.is_deleted.is_(False),
            )
        )
        if not row.scalar_one_or_none():
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Source generation not found"
            )

    cp = ContentPiece(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        title=payload.title,
        body=payload.body,
        format=payload.format,
        status=ContentStatus.DRAFT,
        source_generation_id=src_id,
        metadata_json=_content_metadata(
            None,
            set_next_action=payload.next_action is not None,
            next_action=payload.next_action,
            set_due_at=payload.due_at is not None,
            due_at=payload.due_at,
            set_scheduled_publish=payload.scheduled_publish is not None,
            scheduled_publish=payload.scheduled_publish,
        ),
    )
    db.add(cp)
    await db.commit()
    await db.refresh(cp)

    await authz_client.bind_resource_to_tenant(
        "content_piece", str(cp.id), str(current.tenant_id), str(current.id)
    )
    return _out(cp)


@router.post(
    "/from-generation",
    response_model=ContentPieceOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_from_generation(
    payload: ContentPieceFromGeneration,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Promote a completed generation's output into an editable content piece."""
    try:
        gen_id = UUID(payload.generation_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid generation_id")

    if not await authz_client.check(str(current.id), "reader", f"generation:{gen_id}"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Not permitted to read this generation"
        )

    row = await db.execute(
        select(Generation).where(
            Generation.id == gen_id,
            Generation.tenant_id == current.tenant_id,
            Generation.is_deleted.is_(False),
        )
    )
    gen = row.scalar_one_or_none()
    if not gen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Generation not found")
    if gen.status != GenerationStatus.COMPLETE or not gen.result:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Generation not ready (status={gen.status.value})",
        )

    title = payload.title or (gen.brief[:80].strip() or "Untitled")
    cp = ContentPiece(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        title=title,
        body=gen.result,
        format=(gen.metadata_json or {}).get("format")
        or (
            "blog_post"
            if (gen.metadata_json or {}).get("kind")
            in ("article_outline", "article_draft")
            else None
        ),
        status=ContentStatus.DRAFT,
        source_generation_id=gen.id,
        metadata_json=article_content_metadata(
            _content_metadata(
                None,
                set_next_action=payload.next_action is not None,
                next_action=payload.next_action,
                set_due_at=payload.due_at is not None,
                due_at=payload.due_at,
                set_scheduled_publish=payload.scheduled_publish is not None,
                scheduled_publish=payload.scheduled_publish,
            ),
            (gen.metadata_json or {}).get("article"),
        ),
    )
    db.add(cp)
    await db.commit()
    await db.refresh(cp)

    await authz_client.bind_resource_to_tenant(
        "content_piece", str(cp.id), str(current.tenant_id), str(current.id)
    )
    return _out(cp)


@router.get("", response_model=list[ContentPieceOut])
async def list_content(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
    page: Annotated[Page, Depends(pagination)],
):
    base = (
        select(ContentPiece)
        .where(
            ContentPiece.tenant_id == current.tenant_id,
            ContentPiece.is_deleted.is_(False),
        )
        .order_by(ContentPiece.updated_at.desc())
    )
    stmt = await paginate(db, base, page, response)
    row = await db.execute(stmt)
    return [_out(cp) for cp in row.scalars().all()]


@router.get("/publish/github/config", response_model=GitHubPublishConfigOut)
async def github_publish_config(
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_reader(current)
    settings = get_settings()
    token, credential, source = await _resolve_github_token(db, current.tenant_id)
    return GitHubPublishConfigOut(
        configured=bool(token),
        api_url=settings.GITHUB_API_URL,
        source=source,
        has_tenant_credential=credential is not None,
        token_last4=credential.token_last4 if credential else None,
        display_name=credential.display_name if credential else None,
    )


@router.post(
    "/publish/github/credentials",
    response_model=GitHubCredentialOut,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_github_credential(
    payload: GitHubCredentialUpsert,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    try:
        await validate_token(payload.token)
    except GitHubPublishError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    try:
        token_encrypted = encrypt_secret(payload.token)
    except CredentialCryptoError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e

    credential = await _load_github_credential(db, current.tenant_id)
    if credential is None:
        credential = GitHubCredential(
            tenant_id=current.tenant_id,
            owner_id=current.id,
            token_encrypted=token_encrypted,
            token_last4=payload.token[-4:],
            display_name=payload.display_name,
        )
        db.add(credential)
    else:
        credential.owner_id = current.id
        credential.token_encrypted = token_encrypted
        credential.token_last4 = payload.token[-4:]
        credential.display_name = payload.display_name
    await record_audit_event(
        db,
        action="github.credentials.connected",
        tenant_id=current.tenant_id,
        actor_user_id=current.id,
        actor_email=current.email,
        details={"display_name": credential.display_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(credential)
    settings = get_settings()
    return GitHubCredentialOut(
        configured=True,
        source="tenant",
        token_last4=credential.token_last4,
        display_name=credential.display_name,
        api_url=settings.GITHUB_API_URL,
    )


@router.delete("/publish/github/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def delete_github_credential(
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _assert_tenant_writer(current)
    credential = await _load_github_credential(db, current.tenant_id)
    if credential:
        credential.is_deleted = True
        await record_audit_event(
            db,
            action="github.credentials.disconnected",
            tenant_id=current.tenant_id,
            actor_user_id=current.id,
            actor_email=current.email,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{content_id}", response_model=ContentPieceOut)
async def get_content(
    content_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(
        str(current.id), "reader", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    return _out(await _load(db, current.tenant_id, content_id))


@router.patch("/{content_id}", response_model=ContentPieceOut)
async def update_content(
    content_id: UUID,
    payload: ContentPieceUpdate,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(
        str(current.id), "writer", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    cp = await _load(db, current.tenant_id, content_id)
    edits_body = any(
        field in payload.model_fields_set for field in ("title", "body", "format")
    )
    if edits_body and cp.status not in _EDITABLE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot edit content in status {cp.status.value}",
        )
    if payload.title is not None:
        cp.title = payload.title
    if payload.body is not None:
        cp.body = payload.body
    if payload.format is not None:
        cp.format = payload.format
    set_scheduled_publish = (
        "scheduled_publish" in payload.model_fields_set
        or payload.clear_scheduled_publish
    )
    if (
        "next_action" in payload.model_fields_set
        or "due_at" in payload.model_fields_set
        or set_scheduled_publish
    ):
        cp.metadata_json = _content_metadata(
            cp.metadata_json,
            set_next_action="next_action" in payload.model_fields_set,
            next_action=payload.next_action,
            set_due_at="due_at" in payload.model_fields_set,
            due_at=payload.due_at,
            set_scheduled_publish=set_scheduled_publish,
            scheduled_publish=(
                None if payload.clear_scheduled_publish else payload.scheduled_publish
            ),
        )
    await db.commit()
    await db.refresh(cp)
    return _out(cp)


@router.post("/{content_id}/transition", response_model=ContentPieceOut)
async def transition_content(
    content_id: UUID,
    payload: ContentPieceTransition,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(
        str(current.id), "writer", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    try:
        target = ContentStatus(payload.status)
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unknown status: {payload.status}"
        )
    cp = await _load(db, current.tenant_id, content_id)
    if target == cp.status:
        return _out(cp)
    if target not in _TRANSITIONS[cp.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Illegal transition {cp.status.value} → {target.value}",
        )
    cp.status = target
    await db.commit()
    await db.refresh(cp)
    return _out(cp)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(
        str(current.id), "writer", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    cp = await _load(db, current.tenant_id, content_id)
    cp.is_deleted = True
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{content_id}/export.md")
async def export_markdown(
    content_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Smallest useful publishing primitive: content as a Markdown file with
    YAML frontmatter (prerequisite for GitHub PR publishing)."""
    if not await authz_client.check(
        str(current.id), "reader", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    cp = await _load(db, current.tenant_id, content_id)
    return Response(
        content=_render_markdown(cp),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{cp.id}.md"'},
    )


@router.post(
    "/{content_id}/publish/github",
    response_model=PublicationOut,
    status_code=status.HTTP_201_CREATED,
)
async def publish_github(
    content_id: UUID,
    payload: PublishGitHubRequest,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Publish an approved content piece to a GitHub repo as a pull request."""
    if not await authz_client.check(
        str(current.id), "writer", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    cp = await _load(db, current.tenant_id, content_id)
    if cp.status not in (ContentStatus.APPROVED, ContentStatus.PUBLISHED):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Approve before publishing (status={cp.status.value})",
        )
    token, _, _ = await _resolve_github_token(db, current.tenant_id)
    if not token:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "GitHub publishing not configured — set GITHUB_TOKEN.",
        )

    path = payload.path or f"content/{cp.id}.md"
    branch = payload.branch or f"opengrow/{cp.id}"
    pub = Publication(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        content_piece_id=cp.id,
        channel=PublicationChannel.GITHUB_PR,
        status=PublicationStatus.PUBLISHING,
        target={
            "repo": payload.repo,
            "path": path,
            "branch": branch,
            "base_branch": payload.base_branch,
        },
    )
    db.add(pub)
    await db.commit()
    await db.refresh(pub)

    try:
        result = await publish_markdown(
            repo=payload.repo,
            path=path,
            content=_render_markdown(cp),
            branch=branch,
            commit_message=payload.commit_message or f"content: {cp.title}",
            pr_title=payload.pr_title or cp.title,
            pr_body=payload.pr_body
            or f"Published via OpenGrow — content piece {cp.id}.",
            base_branch=payload.base_branch,
            token=token,
            draft=payload.draft,
            labels=payload.labels,
            reviewers=payload.reviewers,
        )
    except GitHubPublishError as e:
        pub.status = PublicationStatus.FAILED
        pub.error_message = str(e)[:500]
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"GitHub publish failed: {e}")

    pub.status = PublicationStatus.PR_OPENED
    pub.url = result["pr_url"]
    pub.external_ref = f"PR #{result['pr_number']} ({result['branch']})"
    pub.target = {
        **(pub.target or {}),
        "pr_number": result["pr_number"],
        "commit_sha": result.get("commit_sha"),
        "base_branch": result["base_branch"],
        "warnings": result.get("warnings") or None,
    }
    await record_audit_event(
        db,
        action="content.published",
        tenant_id=current.tenant_id,
        actor_user_id=current.id,
        actor_email=current.email,
        ref_type="content_piece",
        ref_id=str(cp.id),
        details={"channel": "GITHUB_PR"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(pub)
    return _pub_out(pub)


_SAFE_TARGET_KEYS = ("site_url", "admin_api_url", "status")


@router.get("/publish/channels", response_model=list[PublishChannelOut])
async def publish_channels(current: Annotated[User, Depends(get_current_user)]):
    """Advertised publishing channels + whether each is implemented."""
    channels = [PublishChannelOut(channel="GITHUB_PR", implemented=True)]
    channels += [
        PublishChannelOut(channel=c, implemented=is_implemented(c))
        for c in KNOWN_CHANNELS
    ]
    return channels


@router.post(
    "/{content_id}/publish",
    response_model=PublicationOut,
    status_code=status.HTTP_201_CREATED,
)
async def publish_content(
    content_id: UUID,
    payload: PublishRequest,
    request: Request,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Publish an approved content piece to a generic channel (WordPress, Ghost,
    …). GitHub PR has its own endpoint (/publish/github)."""
    if not await authz_client.check(
        str(current.id), "writer", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    cp = await _load(db, current.tenant_id, content_id)
    if cp.status not in (ContentStatus.APPROVED, ContentStatus.PUBLISHED):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Approve before publishing (status={cp.status.value})",
        )

    channel = payload.channel
    if channel == "GITHUB_PR":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Use /content/{id}/publish/github for GitHub PR publishing",
        )
    try:
        channel_enum = PublicationChannel(channel)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown channel: {channel}")

    adapter = get_adapter(channel)
    safe_target = {"channel": channel} | {
        k: v for k, v in payload.config.items() if k in _SAFE_TARGET_KEYS
    }
    pub = Publication(
        tenant_id=current.tenant_id,
        owner_id=current.id,
        content_piece_id=cp.id,
        channel=channel_enum,
        status=PublicationStatus.PUBLISHING,
        target=safe_target,
    )
    db.add(pub)
    await db.commit()
    await db.refresh(pub)

    try:
        result = await adapter.publish(
            title=cp.title, body=_render_markdown(cp), config=payload.config
        )
    except PublisherError as e:
        pub.status = PublicationStatus.FAILED
        pub.error_message = str(e)[:500]
        await db.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"{channel} publish failed: {e}"
        )

    pub.status = PublicationStatus.PUBLISHED
    pub.url = result["url"]
    pub.external_ref = result["external_ref"]
    await record_audit_event(
        db,
        action="content.published",
        tenant_id=current.tenant_id,
        actor_user_id=current.id,
        actor_email=current.email,
        ref_type="content_piece",
        ref_id=str(cp.id),
        details={"channel": channel},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await record_usage(
        db,
        tenant_id=current.tenant_id,
        user_id=current.id,
        kind="publish",
        ref_type="publication",
        ref_id=str(pub.id),
        details={"channel": channel},
    )
    await db.refresh(pub)
    return _pub_out(pub)


@router.get("/{content_id}/publications", response_model=list[PublicationOut])
async def list_publications(
    content_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(
        str(current.id), "reader", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    await _load(db, current.tenant_id, content_id)  # 404s if missing in tenant
    row = await db.execute(
        select(Publication)
        .where(
            Publication.content_piece_id == content_id,
            Publication.tenant_id == current.tenant_id,
            Publication.is_deleted.is_(False),
        )
        .order_by(Publication.created_at.desc())
    )
    return [_pub_out(p) for p in row.scalars().all()]


@router.post(
    "/{content_id}/publications/{publication_id}/refresh",
    response_model=PublicationOut,
)
async def refresh_publication(
    content_id: UUID,
    publication_id: UUID,
    current: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await authz_client.check(
        str(current.id), "writer", f"content_piece:{content_id}"
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted")
    cp = await _load(db, current.tenant_id, content_id)
    row = await db.execute(
        select(Publication).where(
            Publication.id == publication_id,
            Publication.content_piece_id == content_id,
            Publication.tenant_id == current.tenant_id,
            Publication.channel == PublicationChannel.GITHUB_PR,
            Publication.is_deleted.is_(False),
        )
    )
    pub = row.scalar_one_or_none()
    if not pub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publication not found")
    repo = (pub.target or {}).get("repo")
    pr_number = _publication_pr_number(pub)
    if not isinstance(repo, str) or not repo.strip() or pr_number is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Publication is missing GitHub repo or PR number",
        )
    token, _, _ = await _resolve_github_token(db, current.tenant_id)
    if not token:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "GitHub publishing not configured — set GITHUB_TOKEN.",
        )

    try:
        result = await get_pull_request_status(
            repo=repo, pr_number=pr_number, token=token
        )
    except GitHubPublishError as e:
        pub.error_message = str(e)[:500]
        await db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"GitHub refresh failed: {e}")

    pub.url = result["pr_url"]
    pub.target = {**(pub.target or {}), **result}
    pub.error_message = None
    if result["merged"]:
        pub.status = PublicationStatus.PUBLISHED
        cp.status = ContentStatus.PUBLISHED
    elif result["state"] == "closed":
        pub.status = PublicationStatus.FAILED
        pub.error_message = "GitHub PR closed without merge"
    else:
        pub.status = PublicationStatus.PR_OPENED
    await db.commit()
    await db.refresh(pub)
    return _pub_out(pub)
