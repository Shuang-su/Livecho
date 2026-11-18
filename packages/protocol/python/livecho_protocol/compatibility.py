"""Exact minor, minimum-version, capability, and manifest negotiation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import Decision, StableCode
from .models import (
    BASE_CAPABILITIES,
    MINIMUM_VIEWER_VERSION,
    MINIMUM_WORKER_VERSION,
    MINOR1_CAPABILITIES,
    ModelManifestRefV1,
    ViewerSubscribeV1,
    WorkerHelloV1,
)
from .scalars import SEMVER_PATTERN

COMPATIBILITY_MATRIX = {
    "viewer": {"major": 1, "accepted_minors": [0, 1], "minimum_client_version": "0.1.0"},
    "worker": {"major": 1, "accepted_minors": [0, 1], "minimum_client_version": "0.1.0"},
}
SERVER_MINORS = frozenset({0, 1})


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


def _selected_worker_minor(offered: set[int], capabilities: set[str]) -> int | None:
    """Pick the negotiated minor without changing the historical minor-0 miss.

    An offer of only minor 1 with the minor-0 capability pair stays
    ``unsupported_minor``. That is the existing golden
    ``version.worker_supported_minor_missing``. Minor 1 is selected only when
    the offer includes it and the capability set is exactly the minor-1 triple.
    """
    intersection = offered & SERVER_MINORS
    if not intersection:
        return None
    eligible: set[int] = set()
    if 0 in intersection and capabilities == set(BASE_CAPABILITIES):
        eligible.add(0)
    if 1 in intersection and capabilities == set(MINOR1_CAPABILITIES):
        eligible.add(1)
    if not eligible:
        if 0 not in intersection:
            return None
        return -1
    return max(eligible)


def negotiate_worker(
    hello: WorkerHelloV1,
    allowlisted_manifests: frozenset[tuple[str, str, str, str]],
) -> NegotiationResult:
    selected = _selected_worker_minor(set(hello.supported_minors), set(hello.capabilities))
    if selected is None:
        return NegotiationResult(Decision(StableCode.UNSUPPORTED_MINOR))
    if not version_at_least(hello.worker_version, MINIMUM_WORKER_VERSION):
        return NegotiationResult(Decision(StableCode.WORKER_VERSION_TOO_OLD))
    if selected < 0:
        return NegotiationResult(Decision(StableCode.CAPABILITY_REQUIRED))
    if not hello.model_manifests or any(
        manifest_key(manifest) not in allowlisted_manifests for manifest in hello.model_manifests
    ):
        return NegotiationResult(Decision(StableCode.MANIFEST_NOT_ALLOWED))
    return NegotiationResult(Decision(StableCode.ACCEPTED), selected_minor=selected)


def negotiate_viewer(subscribe: ViewerSubscribeV1) -> NegotiationResult:
    offered = set(subscribe.supported_minors)
    intersection = offered & SERVER_MINORS
    # A viewer offer of only minor 1 is the historical missing-minor golden.
    # Minor 1 is selected when both 0 and 1 are offered.
    if 0 not in intersection:
        return NegotiationResult(Decision(StableCode.UNSUPPORTED_MINOR))
    if not version_at_least(subscribe.client_version, MINIMUM_VIEWER_VERSION):
        return NegotiationResult(Decision(StableCode.WORKER_VERSION_TOO_OLD))
    selected = 1 if 1 in intersection else 0
    return NegotiationResult(Decision(StableCode.ACCEPTED), selected_minor=selected)


Surface = Literal["worker", "viewer"]
