from datetime import datetime, timezone

from app.schemas.content_piece import ContentPieceCreate, ContentPieceUpdate


def test_content_piece_create_accepts_planning_metadata():
    due_at = datetime(2026, 7, 22, 12, 0, tzinfo=timezone.utc)
    payload = ContentPieceCreate(
        title="Launch page",
        next_action=" Approve copy ",
        due_at=due_at,
    )

    assert payload.next_action == "Approve copy"
    assert payload.due_at == due_at


def test_content_piece_update_treats_blank_next_action_as_none():
    payload = ContentPieceUpdate(next_action=" ")

    assert payload.next_action is None
