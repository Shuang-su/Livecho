"""In-memory fixtures for worker-identity tests. Keys stay in process memory."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from livecho_backend.auth.bootstrap import bootstrap_first_admin
from livecho_backend.auth.crypto import encode_secret
from livecho_backend.auth.records import Account, AccountStatus, Principal, Role
from livecho_backend.auth.store import InviteKind, MemoryAuthStore
from livecho_backend.worker_identity.app import create_worker_identity_app
from livecho_backend.worker_identity.service import WorkerIdentityService
from livecho_backend.worker_identity.store import MemoryWorkerIdentityStore
from livecho_protocol.models import WorkerHelloV1, WorkerStatsV1

from tests.auth.support import Call, Sequence, TickingClock, call_app, json_body

MANIFEST = {
    "provider": "synthetic",
    "model_id": "fixture-asr",
    "revision": "1",
    "sha256": "a" * 64,
}
MESSAGE_ID = "00000000-0000-4000-8000-000000000001"
STAMP = "2026-01-01T00:00:00.000Z"


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def fresh_key() -> tuple[Ed25519PrivateKey, bytes]:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    return private, public


def challenge_message(device_id: str, challenge_id: str, nonce: bytes) -> bytes:
    return (
        b"livecho-worker-challenge-v1\x00"
        + device_id.encode("ascii")
        + b"\x00"
        + challenge_id.encode("ascii")
        + b"\x00"
        + nonce
    )


def hello_for(
    device_id: str,
    *,
    minor1: bool = False,
    manifest: Mapping[str, str] | None = None,
    worker_id: str | None = None,
    supported_minors: list[int] | None = None,
    capabilities: list[str] | None = None,
    manifests: list[Mapping[str, str]] | None = None,
) -> WorkerHelloV1:
    if capabilities is None:
        capabilities = ["asr.transcribe", "protocol.binary-pcm"]
        if minor1:
            capabilities = [*capabilities, "protocol.epoch-rotation"]
    if supported_minors is None:
        supported_minors = [0, 1] if minor1 else [0]
    body: dict[str, Any] = {
        "protocol": "livecho.worker.v1",
        "protocol_minor": 0,
        "message_id": MESSAGE_ID,
        "type": "worker.hello",
        "sent_at": STAMP,
        "worker_id": worker_id or device_id,
        "worker_version": "0.1.0",
        "supported_minors": supported_minors,
        "capabilities": capabilities,
        "model_manifests": list(manifests)
        if manifests is not None
        else [dict(manifest or MANIFEST)],
        "resume": None,
    }
    return WorkerHelloV1.model_validate(body)


def stats_for(
    *,
    accepted: int,
    rejected: int,
    processed_ms: int = 0,
    rtf: float = 1.0,
) -> WorkerStatsV1:
    return WorkerStatsV1.model_validate(
        {
            "protocol": "livecho.worker.v1",
            "protocol_minor": 0,
            "message_id": MESSAGE_ID,
            "type": "worker.stats",
            "sent_at": STAMP,
            "lease_id": "00000000-0000-4000-8000-000000000020",
            "session_id": "00000000-0000-4000-8000-000000000030",
            "stats_id": "00000000-0000-4000-8000-000000000050",
            "epoch": "1",
            "seq": "0",
            "revision": "1",
            "processed_audio_ms": str(processed_ms),
            "segments_accepted": str(accepted),
            "segments_rejected": str(rejected),
            "realtime_factor": rtf,
            "window_started_at": STAMP,
            "window_ended_at": "2026-01-01T00:00:01.000Z",
        }
    )


class World:
    """One auth store plus one worker-identity app. Nothing is written to disk."""

    def __init__(self, *, key: bytes | None = bytes(range(32))) -> None:
        self.clock = TickingClock()
        self.ids = Sequence()
        self.random = Sequence()
        self.auth = MemoryAuthStore()
        self.admin = bootstrap_first_admin(
            self.auth,
            "admin@example.com",
            now=self.clock.now,
            account_id=self.ids.id(),
        )
        self.contributor = self.activate("contributor@example.com", Role.CONTRIBUTOR)
        self.key = key
        self.store = MemoryWorkerIdentityStore()
        self.app = create_worker_identity_app(
            store=self.store,
            accounts=self.auth,
            principal_for_cookie=self.principal_for_cookie,
            enrollment_key=key,
            clock=self.clock,
            random_bytes=self.random.bytes,
            new_id=self.ids.id,
        )
        service = self.app.state.worker_service
        assert isinstance(service, WorkerIdentityService)
        self.service = service

    def activate(self, email: str, role: Role) -> Account:
        kind, account = self.auth.plan_invite(
            email=email,
            role=role,
            now=self.clock.now,
            account_id=self.ids.id(),
        )
        assert kind is InviteKind.CREATED
        claimed = self.auth.claim_account_for_session(account.account_id)
        assert claimed is not None
        return claimed

    def principal_for_cookie(self, cookie: str | None) -> Principal | None:
        if cookie is None:
            return None
        account = self.auth.account_by_id(cookie)
        if account is None or account.status is not AccountStatus.ACTIVE:
            return None
        return Principal(
            account_id=account.account_id,
            role=account.role,
            status=account.status,
        )

    def call(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        account: str | None = None,
        query: str = "",
        client: tuple[str, int] | None = ("203.0.113.10", 4430),
        headers: Mapping[str, str] | None = None,
    ) -> Call:
        merged = dict(headers or {})
        if account is not None:
            merged["cookie"] = f"livecho_session={account}"
        return call_app(
            self.app,
            method,
            path,
            body=body,
            headers=merged,
            query=query,
            client=client,
        )

    def issue(self, account_id: str | None = None, *, actor: str | None = None) -> Call:
        return self.call(
            "POST",
            "/api/worker/enrollment-tokens",
            body=json_body({"account_id": account_id or self.contributor.account_id}),
            account=self.admin.account_id if actor is None else actor,
        )

    def enroll(
        self,
        token: str,
        public_key: bytes | str,
        *,
        extra: Mapping[str, object] | None = None,
        client: tuple[str, int] | None = ("203.0.113.10", 4430),
    ) -> Call:
        encoded = public_key if isinstance(public_key, str) else encode_secret(public_key)
        payload: dict[str, object] = {"token": token, "public_key": encoded}
        if extra is not None:
            payload.update(extra)
        return self.call(
            "POST",
            "/api/worker/devices",
            body=json_body(payload),
            client=client,
        )

    def challenge(
        self,
        device_id: str,
        *,
        body: bytes | None = None,
        client: tuple[str, int] | None = ("203.0.113.20", 4430),
    ) -> Call:
        return self.call(
            "POST",
            f"/api/worker/devices/{device_id}/challenges",
            body=b"{}" if body is None else body,
            client=client,
        )

    def verify(
        self,
        challenge_id: str,
        device_id: str,
        signature: bytes,
        *,
        client: tuple[str, int] | None = ("203.0.113.20", 4430),
    ) -> Call:
        return self.call(
            "POST",
            f"/api/worker/challenges/{challenge_id}/verify",
            body=json_body({"device_id": device_id, "signature": b64(signature)}),
            client=client,
        )

    def allow(self, manifest: Mapping[str, str] | None = None) -> Call:
        return self.call(
            "POST",
            "/api/worker/allowlist",
            body=json_body(dict(manifest or MANIFEST)),
            account=self.admin.account_id,
        )


def assert_no_cookie(response: Call) -> None:
    names = [name.lower() for name, _value in response.headers]
    assert "set-cookie" not in names


def assert_stored_json(response: Call, status: int) -> None:
    assert response.status == status
    assert_no_cookie(response)
    cache = response.value("cache-control")
    assert cache == "no-store"
    if response.body:
        assert b": " not in response.body
        assert b", " not in response.body
        content_type = response.value("content-type")
        assert content_type is not None
        assert content_type.startswith("application/json")


def prove(world: World, private: Ed25519PrivateKey, device_id: str) -> None:
    issued = world.challenge(device_id)
    assert_stored_json(issued, 201)
    body = issued.json()
    nonce = b64decode(body["nonce"])
    signature = private.sign(challenge_message(device_id, body["challenge_id"], nonce))
    verified = world.verify(body["challenge_id"], device_id, signature)
    assert verified.status == 204
    assert verified.body == b""
    assert_no_cookie(verified)


def stamp(value: datetime | None = None) -> datetime:
    return value or datetime(2026, 1, 1, tzinfo=UTC)
