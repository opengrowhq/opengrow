"""Seeded global system playbooks (migration 029): upgrade/downgrade behavior,
resolver fallback to the seeded defaults, and prompt composition picking them
up for every generation kind."""

import importlib.util
import uuid
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).parents[1] / "alembic" / "versions" / "029_seed_system_playbooks.py"
)


def _migration():
    spec = importlib.util.spec_from_file_location("migration_029", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_migration(direction: str, connection) -> None:
    """Run 029's upgrade()/downgrade() against an existing connection via
    alembic's operation proxy (same engine the migration runs under)."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    ctx = MigrationContext.configure(connection)
    with Operations.context(ctx):
        getattr(_migration(), direction)()


def _seeded_playbook_rows():
    """ORM-ready (id, kind, name, template) tuples exactly as the migration
    seeds them — used to exercise resolver/prompt behavior without running
    the migration in the shared test DB."""
    module = _migration()
    return [
        (uuid.UUID(module._seed_id(kind)), kind, name, template)
        for kind, name, template in module.SEEDS
    ]


def _clear_stale_global_playbooks(sync_db):
    """Delete pre-existing global rows of the seeded kinds. The
    metadata-created test schema has no partial unique index, so leftovers
    from earlier tests sharing the DB would make the resolver's pick
    ambiguous (and break downgrade's only-the-seeded-rows assertion)."""
    from sqlalchemy import delete, select

    from app.models.playbook import Playbook, PlaybookKind

    kinds = [PlaybookKind(kind) for _id, kind, _n, _t in _seeded_playbook_rows()]
    stale_ids = (
        sync_db.execute(
            select(Playbook.id).where(
                Playbook.tenant_id.is_(None), Playbook.kind.in_(kinds)
            )
        )
        .scalars()
        .all()
    )
    if stale_ids:
        sync_db.execute(delete(Playbook).where(Playbook.id.in_(stale_ids)))
        sync_db.commit()


def _insert_global_playbooks(sync_db):
    """Insert the three seeded global rows (clearing stale globals first);
    callers delete what they inserted."""
    from app.models.playbook import Playbook, PlaybookKind

    _clear_stale_global_playbooks(sync_db)

    rows = []
    for playbook_id, kind, name, template in _seeded_playbook_rows():
        row = Playbook(
            id=playbook_id,
            tenant_id=None,
            kind=PlaybookKind(kind),
            name=name,
            version=1,
            system_template=template,
            is_active=True,
        )
        sync_db.add(row)
        rows.append(row)
    sync_db.commit()
    return rows


def test_migration_seeds_three_global_playbooks_and_is_idempotent(sync_db):
    from sqlalchemy import select

    from app.models.playbook import Playbook

    seeded_ids = {row[0] for row in _seeded_playbook_rows()}
    connection = sync_db.connection()

    def _seeded_rows():
        return (
            sync_db.execute(select(Playbook).where(Playbook.id.in_(seeded_ids)))
            .scalars()
            .all()
        )

    try:
        _run_migration("upgrade", connection)
        rows = _seeded_rows()
        assert len(rows) == 3
        assert {r.kind.value for r in rows} == {
            "ARTICLE_OUTLINE",
            "ARTICLE_DRAFT",
            "GENERIC_COPY",
        }
        for row in rows:
            assert row.tenant_id is None
            assert row.is_active is True
            assert row.is_deleted is False
            assert row.version == 1
            assert (
                row.system_template.count("## Methodology: ")
                == {
                    "ARTICLE_OUTLINE": 9,
                    "ARTICLE_DRAFT": 17,
                    "GENERIC_COPY": 9,
                }[row.kind.value]
            )

        # running upgrade again is a no-op (deterministic ids +
        # ON CONFLICT DO NOTHING)
        _run_migration("upgrade", connection)
        assert len(_seeded_rows()) == 3
    finally:
        _run_migration("downgrade", connection)

    assert _seeded_rows() == []


def test_downgrade_removes_only_the_seeded_rows(sync_db):
    from sqlalchemy import select

    from app.models.playbook import Playbook

    _clear_stale_global_playbooks(sync_db)

    other = Playbook(
        id=uuid.uuid4(),
        tenant_id=None,
        kind="GENERIC_COPY",
        name="inactive other",
        version=1,
        system_template="x",
        is_active=False,  # inactive: no conflict with the partial unique index
    )
    sync_db.add(other)
    sync_db.commit()
    connection = sync_db.connection()
    try:
        _run_migration("upgrade", connection)
        _run_migration("downgrade", connection)
        seeded_ids = {row[0] for row in _seeded_playbook_rows()}
        remaining = sync_db.execute(select(Playbook)).scalars().all()
        assert seeded_ids.isdisjoint({r.id for r in remaining})
        assert other.id in {r.id for r in remaining}
    finally:
        sync_db.delete(other)
        sync_db.commit()


def test_resolver_returns_seeded_global_and_tenant_still_overrides(sync_db):
    from app.core.playbook import get_active_system_template_sync
    from app.models.playbook import Playbook, PlaybookKind
    from app.models.tenant import Tenant

    tenant = Tenant(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
    sync_db.add(tenant)
    sync_db.commit()

    seeded = _insert_global_playbooks(sync_db)
    try:
        # Seeded global is the live default for every kind...
        for playbook_id, kind, _name, template in _seeded_playbook_rows():
            assert (
                get_active_system_template_sync(sync_db, tenant.id, PlaybookKind(kind))
                == template
            )

        # ...and a tenant-specific active playbook still wins.
        override = Playbook(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            kind=PlaybookKind.ARTICLE_OUTLINE,
            name="tenant override",
            version=1,
            system_template="TENANT TEMPLATE",
            is_active=True,
        )
        sync_db.add(override)
        sync_db.commit()
        assert (
            get_active_system_template_sync(
                sync_db, tenant.id, PlaybookKind.ARTICLE_OUTLINE
            )
            == "TENANT TEMPLATE"
        )
        # other kinds still fall back to the seeded global
        assert (
            get_active_system_template_sync(
                sync_db, tenant.id, PlaybookKind.ARTICLE_DRAFT
            )
            == dict(
                (kind, template) for _id, kind, _n, template in _seeded_playbook_rows()
            )["ARTICLE_DRAFT"]
        )
        sync_db.delete(override)
        sync_db.commit()
    finally:
        for row in seeded:
            sync_db.delete(row)
        sync_db.commit()


def test_build_generation_messages_picks_up_seeded_templates(sync_db):
    from app.core.auth import hash_password
    from app.core.generation_messages import build_generation_messages
    from app.models.generation import Generation, GenerationStatus
    from app.models.tenant import Tenant
    from app.models.user import User

    tenant = Tenant(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="T")
    sync_db.add(tenant)
    sync_db.commit()
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=f"u-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pw-123456"),
        display_name="U",
    )
    sync_db.add(user)
    sync_db.commit()

    seeded = _insert_global_playbooks(sync_db)
    templates = {kind: template for _id, kind, _n, template in _seeded_playbook_rows()}
    try:
        cases = [
            (
                "article_outline",
                {"kind": "article_outline", "article": {"topic": "why founders blog"}},
                templates["ARTICLE_OUTLINE"],
                "## Methodology: outline-first-writing",
            ),
            (
                "article_draft",
                {
                    "kind": "article_draft",
                    "article": {"topic": "why founders blog"},
                    "outline": [],
                },
                templates["ARTICLE_DRAFT"],
                "## Methodology: blog-formatting",
            ),
            (
                "generic",
                {},
                templates["GENERIC_COPY"],
                "## Methodology: cms-export-mapping",
            ),
        ]
        for label, metadata, template, marker in cases:
            gen = Generation(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                owner_id=user.id,
                brief=f"brief for {label}",
                status=GenerationStatus.QUEUED,
                metadata_json=metadata,
            )
            sync_db.add(gen)
            sync_db.commit()

            messages, _max_tokens = build_generation_messages(sync_db, gen)
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == template
            assert marker in messages[0]["content"]

            sync_db.delete(gen)
            sync_db.commit()
    finally:
        for row in seeded:
            sync_db.delete(row)
        sync_db.commit()
