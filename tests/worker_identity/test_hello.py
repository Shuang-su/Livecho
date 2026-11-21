"""Hello admission calls negotiate_worker and does not invent protocol codes."""

from __future__ import annotations

from livecho_backend.auth.records import AccountStatus

from .support import MANIFEST, World, fresh_key, hello_for, prove


def _admitted_device(world: World) -> str:
    private, public = fresh_key()
    created = world.enroll(world.issue().json()["token"], public)
    device_id = created.json()["device_id"]
    assert isinstance(device_id, str)
    prove(world, private, device_id)
    return device_id


def test_manifest_mismatch_keeps_manifest_not_allowed() -> None:
    world = World()
    device_id = _admitted_device(world)
    world.allow()
    mismatched = dict(MANIFEST)
    mismatched["sha256"] = "b" * 64
    decision = world.service.admit_hello(hello_for(device_id, manifest=mismatched), device_id)
    assert decision.accepted is False
    assert decision.protocol_code == "manifest_not_allowed"
    assert decision.audit_result == "capability_rejected"
    audit = [item for item in world.store.audits() if item.result == "capability_rejected"][-1]
    assert audit.object_class == "hello"
    assert audit.device_id == device_id
    assert "a" * 64 not in repr(audit)
    again = world.service.admit_hello(hello_for(device_id), device_id)
    assert again.audit_result == "signature_invalid"
    assert again.accepted is False


def test_minor_1_epoch_rotation_hello_is_admitted() -> None:
    world = World()
    device_id = _admitted_device(world)
    assert world.allow().status == 201
    hello = hello_for(device_id, minor1=True)
    assert "protocol.epoch-rotation" in hello.capabilities
    decision = world.service.admit_hello(hello, device_id)
    assert decision.accepted is True
    assert decision.protocol_code == "accepted"
    assert decision.selected_minor == 1
    assert decision.audit_result == "ok"
    second = world.service.admit_hello(hello, device_id)
    assert second.accepted is False
    assert second.audit_result == "signature_invalid"


def test_minor_0_hello_and_other_negotiate_rejections() -> None:
    world = World()
    device_id = _admitted_device(world)
    world.allow()
    accepted = world.service.admit_hello(hello_for(device_id), device_id)
    assert accepted.accepted is True
    assert accepted.selected_minor == 0
    other = World()
    original_private, public = fresh_key()
    created = other.enroll(other.issue().json()["token"], public)
    other_id = created.json()["device_id"]
    other.allow()
    prove(other, original_private, other_id)
    required = other.service.admit_hello(
        hello_for(
            other_id,
            supported_minors=[0],
            capabilities=[
                "asr.transcribe",
                "protocol.binary-pcm",
                "protocol.epoch-rotation",
            ],
        ),
        other_id,
    )
    assert required.protocol_code == "capability_required"
    assert required.audit_result == "capability_rejected"
    prove(other, original_private, other_id)
    empty = other.service.admit_hello(hello_for(other_id, manifests=[]), other_id)
    assert empty.protocol_code == "manifest_not_allowed"
    assert empty.audit_result == "capability_rejected"
    prove(other, original_private, other_id)
    unsupported = other.service.admit_hello(
        hello_for(other_id, supported_minors=[2], capabilities=["asr.transcribe"]),
        other_id,
    )
    assert unsupported.protocol_code == "unsupported_minor"
    assert unsupported.audit_result == "rejected"
    account = other.auth.account_by_id(other.contributor.account_id)
    assert account is not None
    assert account.status is AccountStatus.ACTIVE


def test_revoked_device_and_unknown_device_are_audited_without_payloads() -> None:
    world = World()
    private, public = fresh_key()
    device_id = world.enroll(world.issue().json()["token"], public).json()["device_id"]
    world.allow()
    prove(world, private, device_id)
    world.store.revoke(device_id, world.clock.now)
    revoked = world.service.admit_hello(hello_for(device_id), device_id)
    assert revoked.audit_result == "device_revoked"
    assert revoked.accepted is False
    unknown = world.service.admit_hello(
        hello_for("00000000-0000-4000-8000-000000000099"),
        "00000000-0000-4000-8000-000000000099",
    )
    assert unknown.audit_result == "rejected"
    assert unknown.accepted is False
    omitted = [item for item in world.store.audits() if item.result == "rejected"][-1]
    assert omitted.device_id is None
    assert omitted.account_id is None
    assert "contributor@example.com" not in repr(omitted)
