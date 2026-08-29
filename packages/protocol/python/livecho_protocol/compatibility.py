"""Exact minor, minimum-version, capability, and manifest negotiation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import Decision, StableCode
from .models import (
    MINIMUM_VIEWER_VERSION,
    MINIMUM_WORKER_VERSION,
    ModelManifestRefV1,
    ViewerSubscribeV1,
    WorkerHelloV1,
)
from .scalars import SEMVER_PATTERN

REQUIRED_CAPABILITIES = frozenset({"asr.transcribe", "protocol.binary-pcm"})

COMPATIBILITY_MATRIX = {
    "viewer": {"major": 1, "accepted_minors": [0], "minimum_client_version": "0.1.0"},
    "worker": {"major": 1, "accepted_minors": [0], "minimum_client_version": "0.1.0"},
}


@dataclass(frozen=True, slots=True)
class NegotiationResult:
    decision: Decision
    selected_minor: int | None = None


def _semver_key(value: str) -> tuple[int, int, int, tuple[tuple[int, int | str], ...]]:
    match = SEMVER_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("invalid SemVer")
    major, minor, patch, prerelease = match.groups()
    if prerelease is None:
        pre_key: tuple[tuple[int, int | str], ...] = ((2, 0),)
    else:
        identifiers: list[tuple[int, int | str]] = []
        for identifier in prerelease.split("."):
            identifiers.append((0, int(identifier)) if identifier.isdigit() else (1, identifier))
        pre_key = tuple(identifiers)
    return int(major), int(minor), int(patch), pre_key


def version_at_least(value: str, minimum: str) -> bool:
    return _semver_key(value) >= _semver_key(minimum)


def manifest_key(manifest: ModelManifestRefV1) -> tuple[str, str, str, str]:
    return manifest.provider, manifest.model_id, manifest.revision, manifest.sha256


def negotiate_worker(
    hello: WorkerHelloV1,
    allowlisted_manifests: frozenset[tuple[str, str, str, str]],
) -> NegotiationResult:
    if 0 not in hello.supported_minors:
        return NegotiationResult(Decision(StableCode.UNSUPPORTED_MINOR))
    if not version_at_least(hello.worker_version, MINIMUM_WORKER_VERSION):
        return NegotiationResult(Decision(StableCode.WORKER_VERSION_TOO_OLD))
    if set(hello.capabilities) != REQUIRED_CAPABILITIES:
        return NegotiationResult(Decision(StableCode.CAPABILITY_REQUIRED))
    if not hello.model_manifests or any(
        manifest_key(manifest) not in allowlisted_manifests for manifest in hello.model_manifests
    ):
        return NegotiationResult(Decision(StableCode.MANIFEST_NOT_ALLOWED))
    return NegotiationResult(Decision(StableCode.ACCEPTED), selected_minor=0)


def negotiate_viewer(subscribe: ViewerSubscribeV1) -> NegotiationResult:
    if 0 not in subscribe.supported_minors:
        return NegotiationResult(Decision(StableCode.UNSUPPORTED_MINOR))
    if not version_at_least(subscribe.client_version, MINIMUM_VIEWER_VERSION):
        return NegotiationResult(Decision(StableCode.WORKER_VERSION_TOO_OLD))
    return NegotiationResult(Decision(StableCode.ACCEPTED), selected_minor=0)


Surface = Literal["worker", "viewer"]
