"""Enrollment tokens are shown once, stored as verifiers, and expire absolutely."""

from __future__ import annotations

import logging
from dataclasses import fields
from datetime import timedelta

import pytest
from livecho_backend.auth.crypto import decode_secret, magic_link_verifier, session_verifier
from livecho_backend.auth.records import AccountStatus, Role
from livecho_backend.worker_identity.crypto import enrollment_verifier
from livecho_backend.worker_identity.records import ENROLLMENT_TTL, Enrollment

from tests.auth.support import json_body

from .support import World, assert_no_cookie, assert_stored_json, fresh_key


def test_enrollment_label_does_not_match_auth_labels() -> None:
    key = bytes(range(32))
    token = bytes(range(32, 64))
    verifier = enrollment_verifier(key, token)
    assert verifier != magic_link_verifier(key, token)
    assert verifier != session_verifier(key, token)


def test_token_is_shown_once_and_only_the_verifier_is_stored(
    caplog: pytest.LogCaptureFixture,
) -> None:
    world = World()
    with caplog.at_level(logging.INFO, logger="livecho.worker_identity"):
        issued = world.issue()
    assert_stored_json(issued, 201)
    body = issued.json()
    assert set(body) == {"enrollment_id", "account_id", "expires_at", "token"}
    assert body["account_id"] == world.contributor.account_id
    assert body["expires_at"] == "2026-01-02T00:00:00.000Z"
    token = decode_secret(body["token"])
    assert token is not None
    rows = world.store.enrollments()
    assert len(rows) == 1
    row = rows[0]
    assert {item.name for item in fields(Enrollment)} == {
        "enrollment_id",
        "account_id",
        "verifier",
        "created_at",
        "expires_at",
        "used_at",
    }
    assert row.verifier == enrollment_verifier(world.key or b"", token)
    assert row.used_at is None
    assert row.expires_at - row.created_at == ENROLLMENT_TTL
    assert body["token"] not in repr(row)
    text = caplog.text
    assert body["token"] not in text
    assert "contributor@example.com" not in text
    assert "device.issue_enrollment" in text

    again = world.issue()
    assert_stored_json(again, 409)
    assert again.json() == {"error": "enrollment_pending"}
    assert "token" not in again.json()
    assert len(world.store.enrollments()) == 1


def test_token_expires_at_24_hours_and_a_second_use_fails() -> None:
    world = World()
    private, public = fresh_key()
    issued = world.issue().json()
    world.clock.advance(timedelta(hours=24) - timedelta(milliseconds=1))
    enrolled = world.enroll(issued["token"], public)
    assert_stored_json(enrolled, 201)
    assert set(enrolled.json()) == {"device_id", "account_id"}
    assert enrolled.json()["account_id"] == world.contributor.account_id
    assert_no_cookie(enrolled)
    again = world.enroll(issued["token"], public)
    assert_stored_json(again, 401)
    assert again.json() == {"error": "rejected"}
    assert len(world.store.devices_for(world.contributor.account_id)) == 1
    assert world.store.enrollments()[0].used_at is not None

    expired = world.issue().json()
    world.clock.advance(timedelta(hours=24))
    rejected = world.enroll(expired["token"], public)
    assert_stored_json(rejected, 401)
    assert world.store.enrollments()[-1].used_at is None
    assert len(world.store.devices_for(world.contributor.account_id)) == 1
    del private


def test_ineligible_and_unknown_accounts_do_not_mint_a_token() -> None:
    world = World()
    viewer = world.activate("viewer@example.com", Role.VIEWER)
    unknown = "00000000-0000-4000-8000-000000000099"
    forbidden = world.issue(unknown, actor=viewer.account_id)
    assert_stored_json(forbidden, 403)
    assert forbidden.json() == {"error": "forbidden"}
    assert world.store.enrollments() == ()

    anonymous = world.call(
        "POST",
        "/api/worker/enrollment-tokens",
        body=json_body({"account_id": world.contributor.account_id}),
    )
    assert_stored_json(anonymous, 401)
    assert anonymous.json() == {"error": "unauthenticated"}

    missing = world.issue(unknown)
    assert_stored_json(missing, 404)
    assert missing.json() == {"error": "not_found"}
    assert world.store.audits()[-1].account_id is None

    invited_kind = world.auth.plan_invite(
        email="invited@example.com",
        role=Role.CONTRIBUTOR,
        now=world.clock.now,
        account_id=world.ids.id(),
    )
    invited = world.issue(invited_kind[1].account_id)
    assert_stored_json(invited, 409)
    assert invited.json() == {"error": "account_ineligible"}

    world.auth.disable_account(world.contributor.account_id, world.clock.now)
    disabled = world.issue()
    assert disabled.json() == {"error": "account_ineligible"}
    assert world.store.enrollments() == ()


def test_missing_key_stores_nothing_and_ignores_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "not-a-real-key")
    monkeypatch.setenv("LIVECHO_SESSION_SIGNING_KEY", "a" * 43)
    monkeypatch.setenv("LIVECHO_EMAIL_ENABLED", "true")
    world = World(key=None)
    issued = world.issue()
    assert_stored_json(issued, 503)
    assert issued.json() == {"error": "unavailable"}
    assert world.store.enrollments() == ()
    short = World(key=b"short")
    assert short.issue().status == 503
    assert short.store.enrollments() == ()


def test_private_key_field_does_not_consume_the_token() -> None:
    world = World()
    _private, public = fresh_key()
    token = world.issue().json()["token"]
    rejected = world.enroll(token, public, extra={"private_key": "secret"})
    assert_stored_json(rejected, 422)
    assert rejected.json() == {"error": "invalid_body"}
    assert world.store.enrollments()[0].used_at is None
    assert world.store.devices_for(world.contributor.account_id) == ()
    created = world.enroll(token, public)
    assert created.status == 201
    device = world.store.device(created.json()["device_id"])
    assert device is not None
    assert device.public_key == public
    assert {item.name for item in fields(device)} == {
        "device_id",
        "account_id",
        "public_key",
        "status",
        "created_at",
        "revoked_at",
    }


def test_disabled_contributor_consumes_a_previously_issued_token() -> None:
    world = World()
    _private, public = fresh_key()
    token = world.issue().json()["token"]
    world.auth.disable_account(world.contributor.account_id, world.clock.now)
    rejected = world.enroll(token, public)
    assert_stored_json(rejected, 401)
    assert world.store.enrollments()[0].used_at is not None
    assert world.store.devices_for(world.contributor.account_id) == ()
    disabled_account = world.auth.account_by_id(world.contributor.account_id)
    assert disabled_account is not None
    assert disabled_account.status is AccountStatus.DISABLED
