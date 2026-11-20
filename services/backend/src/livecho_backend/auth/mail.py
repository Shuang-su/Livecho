"""In-memory mail sink and a transport-injected Resend request builder.

``create_auth_app`` never opens a socket. A Resend transport can be constructed
only when mail is fully configured, and only by an explicit caller.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from .config import AuthConfig, can_send
from .crypto import magic_link_text

RESEND_ENDPOINT = "https://api.resend.com/emails"
SIGN_IN_SUBJECT = "Sign in to Livecho"


@dataclass(frozen=True, slots=True)
class OutboundMail:
    recipient: str
    idempotency_key: str
    text: str

    @property
    def contained_token(self) -> bool:
        return "/login/continue#" in self.text


@dataclass(frozen=True, slots=True)
class PreparedResendCall:
    url: str
    headers: tuple[tuple[str, str], ...]
    body: bytes


class MailSender(Protocol):
    def send(self, message: OutboundMail) -> bool: ...


class MemoryMailSink:
    """Records messages in process memory and writes nothing to disk."""

    def __init__(self, failures: int = 0) -> None:
        self.sent: list[OutboundMail] = []
        self.attempts: list[str] = []
        self._failures = failures

    def send(self, message: OutboundMail) -> bool:
        self.attempts.append(message.idempotency_key)
        if self._failures > 0:
            self._failures -= 1
            return False
        self.sent.append(message)
        return True

    def clear(self) -> None:
        self.sent.clear()
        self.attempts.clear()
        self._failures = 0


def prepare_resend_call(
    message: OutboundMail,
    *,
    sender: str,
    api_key: str,
) -> PreparedResendCall:
    """Build one Resend send. The caller supplies any transport."""
    payload = {
        "from": sender,
        "to": [message.recipient],
        "subject": SIGN_IN_SUBJECT,
        "text": message.text,
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    headers = (
        ("Authorization", f"Bearer {api_key}"),
        ("Content-Type", "application/json"),
        ("Idempotency-Key", message.idempotency_key),
    )
    return PreparedResendCall(url=RESEND_ENDPOINT, headers=headers, body=body)


@dataclass(slots=True)
class TransportMailer:
    """Delivers through an injected transport. Refuses an incomplete config."""

    config: AuthConfig
    transport: Callable[[PreparedResendCall], int]
    calls: list[PreparedResendCall] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not can_send(self.config):
            raise RuntimeError("mail transport refused")

    def send(self, message: OutboundMail) -> bool:
        sender = self.config.email_from
        api_key = self.config.resend_api_key
        if sender is None or api_key is None:
            return False
        prepared = prepare_resend_call(message, sender=sender, api_key=api_key)
        self.calls.append(prepared)
        try:
            status = self.transport(prepared)
        except Exception:
            return False
        return 200 <= status < 300


def link_message(origin: str, token: str, recipient: str, link_id: str) -> OutboundMail:
    return OutboundMail(
        recipient=recipient,
        idempotency_key=link_id,
        text=magic_link_text(origin, token),
    )
