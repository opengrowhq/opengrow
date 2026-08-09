"""Email publisher — send the content as an email (newsletter-style).

config: { to (comma-separated or list), subject?, from?, smtp_host?, smtp_port? }
Uses the app's configured SMTP (Mailpit in lite) unless overridden. BYOK SMTP
via smtp_host/smtp_port for real delivery.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from app.config import settings
from app.core.publishers.base import PublisherError, PublishResult
from app.core.publishers.safety import safe_host


def _recipients(to) -> list[str]:
    if isinstance(to, list):
        items = to
    else:
        items = str(to or "").split(",")
    return [r.strip() for r in items if r.strip()]


def build_message(
    title: str, body: str, to: list[str], sender: str, subject: str | None
) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject or title
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg.set_content(body)
    return msg


def _send(msg: EmailMessage, host: str, port: int) -> None:
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.send_message(msg)


async def publish(*, title: str, body: str, config: dict) -> PublishResult:
    recipients = _recipients(config.get("to"))
    if not recipients:
        raise PublisherError("Email config missing: to")
    sender = config.get("from", "no-reply@opengrow.dev")
    # A caller-supplied SMTP host is untrusted → SSRF-guard it. Falling back to
    # the server-configured relay (trusted env value) needs no check.
    override_host = config.get("smtp_host")
    if override_host:
        port = int(config.get("smtp_port", 587))
        safe_host(override_host, port)
        host = override_host
    else:
        host = settings.MAILPIT_HOST
        port = int(settings.MAILPIT_SMTP_PORT)
    msg = build_message(title, body, recipients, sender, config.get("subject"))
    try:
        await asyncio.to_thread(_send, msg, host, port)
    except OSError as e:
        raise PublisherError(f"Email send failed: {e}") from e
    return {"url": "", "external_ref": f"sent to {len(recipients)} recipient(s)"}
