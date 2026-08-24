"""Resolve the active system-prompt template for a generation kind.

Fallback chain: tenant-specific active playbook -> global (tenant_id NULL)
active playbook -> None (caller falls back to its own hardcoded default).

``get_active_system_template_sync`` takes a sync ``Session`` (Celery worker /
orchestrator context, same convention as ``article_grounding.ground_article``)
since that's the only place a real LLM call — and therefore the real prompt —
is produced. Best-effort: any DB error yields None rather than failing the
caller, matching ``ground_article``'s existing failure behavior.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.playbook import Playbook, PlaybookKind

log = logging.getLogger(__name__)


def get_active_system_template_sync(
    db: Session, tenant_id: UUID, kind: PlaybookKind
) -> str | None:
    try:
        row = (
            db.execute(
                select(Playbook)
                .where(
                    Playbook.kind == kind,
                    Playbook.is_active.is_(True),
                    Playbook.is_deleted.is_(False),
                    or_(
                        Playbook.tenant_id == tenant_id,
                        Playbook.tenant_id.is_(None),
                    ),
                )
                # tenant-specific (non-NULL) row wins over the global default
                .order_by(Playbook.tenant_id.is_(None))
            )
            .scalars()
            .first()
        )
        return row.system_template if row else None
    except Exception as e:
        log.info("playbook lookup skipped: %s", e.__class__.__name__)
        return None
