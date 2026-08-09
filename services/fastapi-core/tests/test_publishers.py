"""Unit tests for publisher adapters (pure request/token building)."""

from datetime import datetime, timezone

import jwt
import pytest

from app.core.publishers import ghost, wordpress
from app.core.publishers.base import PublisherError


def test_wordpress_payload():
    p = wordpress.build_payload("Title", "Body", status="draft")
    assert p == {"title": "Title", "content": "Body", "status": "draft"}


def test_ghost_payload():
    p = ghost.build_payload("Title", "<p>hi</p>")
    assert p["posts"][0]["title"] == "Title"
    assert p["posts"][0]["status"] == "published"


def test_ghost_token_is_signed_with_hex_secret():
    # Ghost secrets are 32 bytes (64 hex chars); PyJWT rejects shorter HMAC keys.
    secret_hex = "ab" * 32
    key = f"keyid:{secret_hex}"
    token = ghost.build_token(key, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    header = jwt.get_unverified_header(token)
    assert header["kid"] == "keyid"
    decoded = jwt.decode(
        token,
        bytes.fromhex(secret_hex),
        algorithms=["HS256"],
        audience="/admin/",
        options={"verify_exp": False},  # token uses the fixed `now` above
    )
    assert decoded["aud"] == "/admin/"


def test_ghost_token_rejects_bad_key():
    with pytest.raises(PublisherError):
        ghost.build_token("no-colon-here")


def test_webflow_item_slugifies():
    from app.core.publishers import webflow

    item = webflow.build_item("My Great Post!", "body text")
    assert item["fieldData"]["name"] == "My Great Post!"
    assert item["fieldData"]["slug"] == "my-great-post"
    assert item["fieldData"]["post-body"] == "body text"


def test_email_recipients_and_message():
    from app.core.publishers import email

    assert email._recipients("a@b.com, c@d.com ") == ["a@b.com", "c@d.com"]
    assert email._recipients(["x@y.com"]) == ["x@y.com"]
    msg = email.build_message("Title", "Body", ["a@b.com"], "s@x.com", None)
    assert msg["Subject"] == "Title" and msg["To"] == "a@b.com"


def test_x_payload_truncates_to_280():
    from app.core.publishers import x

    long_body = "a" * 400
    assert len(x.build_payload(long_body)["text"]) == 280


def test_linkedin_payload_shape():
    from app.core.publishers import linkedin

    p = linkedin.build_payload("urn:li:person:123", "hello")
    assert p["author"] == "urn:li:person:123"
    assert p["lifecycleState"] == "PUBLISHED"
    assert (
        p["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"]
        == "hello"
    )


# ---- SSRF guards (block internal/metadata targets before any connection) ----


async def test_wordpress_blocks_internal_host():
    from app.core.publishers import wordpress

    with pytest.raises(PublisherError):
        await wordpress.publish(
            title="t",
            body="b",
            config={
                "site_url": "http://127.0.0.1:8000",
                "username": "u",
                "app_password": "p",
            },
        )


async def test_wordpress_blocks_cloud_metadata():
    from app.core.publishers import wordpress

    with pytest.raises(PublisherError):
        await wordpress.publish(
            title="t",
            body="b",
            config={
                "site_url": "http://169.254.169.254/",
                "username": "u",
                "app_password": "p",
            },
        )


async def test_ghost_blocks_internal_host():
    from app.core.publishers import ghost

    with pytest.raises(PublisherError):
        await ghost.publish(
            title="t",
            body="b",
            config={
                "admin_api_url": "http://10.0.0.1",
                "admin_api_key": "a:" + "ab" * 32,
            },
        )


async def test_email_blocks_internal_smtp_override():
    from app.core.publishers import email

    with pytest.raises(PublisherError):
        await email.publish(
            title="t",
            body="b",
            config={"to": "x@y.com", "smtp_host": "127.0.0.1", "smtp_port": 5432},
        )
