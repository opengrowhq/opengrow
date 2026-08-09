"""ClamAV clamd network client. Lite mode: auto-clean without contacting ClamAV."""

from __future__ import annotations
import io
import logging

from app.config import settings

log = logging.getLogger("clamav")


def _client():
    import clamd

    return clamd.ClamdNetworkSocket(
        host=settings.CLAMAV_HOST, port=settings.CLAMAV_PORT, timeout=60
    )


def ping() -> bool:
    if settings.is_lite:
        return True
    try:
        return _client().ping() == "PONG"
    except Exception as e:
        log.error("clamav ping failed: %s", e)
        return False


def scan_bytes(data: bytes) -> tuple[bool, str]:
    """Return (clean, message). clean=False on FOUND or ERROR.

    In lite mode always returns (True, "skipped-lite-mode") — appropriate for personal
    single-user deployments where the operator trusts their own uploads. Do NOT use
    lite mode for multi-user deployments.
    """
    if settings.is_lite:
        return True, "skipped-lite-mode"
    try:
        result = _client().instream(io.BytesIO(data))
        stream = result.get("stream")
        if not stream:
            return False, "clamav: no stream verdict"
        verdict, sig = stream
        if verdict == "OK":
            return True, "clean"
        if verdict == "FOUND":
            return False, f"malware detected: {sig}"
        return False, f"clamav error: {verdict}:{sig}"
    except Exception as e:
        log.error("clamav scan failed: %s", e)
        return False, f"clamav exception: {e.__class__.__name__}"
