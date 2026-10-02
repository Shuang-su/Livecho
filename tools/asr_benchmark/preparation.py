"""Model-only transfer control plane, tested using metadata doubles.

The CLI cache registration is intentionally not installed: immutable source
manifests, conversion/provider pins and approvals are still missing. No arbitrary URL,
path, body, request header or server diagnostic is accepted by this control plane.
"""

from contextlib import suppress
from dataclasses import dataclass
from typing import Literal, Protocol

from .contracts import (
    NS,
    Asset,
    Closed,
    Digest,
    Nonnegative,
    PreparationManifest,
    Revision,
    metadata_digest,
)
from .runtime import BlockedEvidence


@dataclass(frozen=True)
class TransferProgress:
    asset_label: str
    received: int
    total: int
    percent: float
    retry_count: int
    outcome: Literal["partial", "retry", "verified", "stopped"]


class TransferCheckpoint(Closed):
    preparation_sha256: Digest
    repository_revision: Revision
    asset_sha256: Digest
    source_mode: Literal["huggingface", "modelscope"]
    received: Nonnegative
    attempts_started: Literal[1, 2, 3]


class ModelCacheBackend(Protocol):
    """Model-only cache outside Git. No network, user paths or audio on this seam."""

    def inspect_partial(self, identity: tuple[str, str, str]) -> tuple[int, str]:
        """Compute actual complete-file length/SHA-256; never trust checkpoint values."""
        ...

    def atomic_promote(self, identity: tuple[str, str, str]) -> None:
        """Promote the same verified inode atomically; forbid symlinks and substitutions."""
        ...

    def invalidate_partial(self, identity: tuple[str, str, str]) -> None: ...


class PreparationTransfer:
    def __init__(
        self,
        manifest: PreparationManifest,
        mode: Literal["huggingface", "modelscope"],
        asset_path: str,
        now_ns: int,
    ) -> None:
        mirrors = [mirror for mirror in manifest.mirrors if mirror.mode == mode]
        assets = [asset for asset in manifest.source_assets if asset.path == asset_path]
        if len(mirrors) != 1 or len(assets) != 1 or now_ns < 0:
            raise BlockedEvidence("preparation_not_allowlisted")
        self.asset: Asset = assets[0]
        self.mode = mode
        self.identity = (metadata_digest(manifest), mirrors[0].revision, self.asset.sha256)
        self.received = 0
        self.last_progress_ns = now_ns
        self.attempt = 1
        self.retry_at_ns: int | None = None
        self.stopped = False
        self.verified = False
        self.promoted = False

    def checkpoint(self) -> str:
        if self.stopped or self.verified:
            raise BlockedEvidence("transfer_closed")
        record = TransferCheckpoint.model_validate(
            {
                "preparation_sha256": self.identity[0],
                "repository_revision": self.identity[1],
                "asset_sha256": self.identity[2],
                "source_mode": self.mode,
                "received": self.received,
                "attempts_started": self.attempt,
            }
        )
        return record.model_dump_json()

    def restore_checkpoint(self, text: str, now_ns: int) -> None:
        """Restore metadata on a fresh controller; retry delay/attempt bounds still apply."""
        from pydantic import ValidationError

        if self.received or self.attempt != 1 or self.stopped or self.verified:
            raise BlockedEvidence("transfer_not_fresh")
        try:
            record = TransferCheckpoint.model_validate_json(text)
        except ValidationError:
            raise BlockedEvidence("checkpoint_invalid") from None
        identity = (record.preparation_sha256, record.repository_revision, record.asset_sha256)
        if identity != self.identity or record.source_mode != self.mode:
            self.stopped = True
            raise BlockedEvidence("partial_revision_changed")
        complete = record.received == self.asset.size
        if (
            record.received > self.asset.size
            or (record.attempts_started >= 3 and not complete)
            or now_ns < 0
        ):
            self.stopped = True
            raise BlockedEvidence("checkpoint_invalid")
        self.received = record.received
        self.attempt = record.attempts_started
        self.last_progress_ns = now_ns
        # A complete interrupted file needs local verification only, never a fourth
        # request or an unsatisfiable Range starting at EOF.
        self.retry_at_ns = None if complete else now_ns + self.attempt * NS

    def promote(self, cache: ModelCacheBackend, now_ns: int) -> TransferProgress:
        """A verified hash is insufficient until same-file atomic promotion succeeds."""
        self.check(now_ns)
        try:
            size, digest = cache.inspect_partial(self.identity)
            self.verify(size, digest, now_ns)
            cache.atomic_promote(self.identity)
            self.promoted = True
            return self.progress("verified")
        except BaseException:
            self.stopped = True
            self.verified = False
            with suppress(BaseException):
                cache.invalidate_partial(self.identity)
            raise BlockedEvidence("promotion_failed") from None

    def progress(
        self, outcome: Literal["partial", "retry", "verified", "stopped"]
    ) -> TransferProgress:
        return TransferProgress(
            self.asset.path,
            self.received,
            self.asset.size,
            100 * self.received / self.asset.size,
            self.attempt - 1,
            outcome,
        )

    def advance(self, received: int, now_ns: int) -> TransferProgress:
        self.check(now_ns)
        if not self.received < received <= self.asset.size:
            self.stopped = True
            raise BlockedEvidence("transfer_length")
        self.received, self.last_progress_ns = received, now_ns
        return self.progress("partial")

    def check(self, now_ns: int) -> None:
        if self.stopped or self.verified:
            raise BlockedEvidence("transfer_closed")
        if now_ns < self.last_progress_ns:
            self.stopped = True
            raise BlockedEvidence("invalid_timing")
        if self.retry_at_ns is not None:
            raise BlockedEvidence("transfer_awaiting_retry")
        if now_ns - self.last_progress_ns >= 60 * NS:
            raise BlockedEvidence("transfer_no_progress")

    def failure(
        self,
        reason: Literal["transient", "no_progress", "authentication", "permission", "integrity"],
        now_ns: int,
    ) -> TransferProgress:
        if self.stopped or self.verified or self.retry_at_ns is not None:
            raise BlockedEvidence("transfer_closed")
        if now_ns < self.last_progress_ns:
            self.stopped = True
            raise BlockedEvidence("invalid_timing")
        if reason in {"authentication", "permission", "integrity"} or self.attempt >= 3:
            self.stopped = True
            return self.progress("stopped")
        self.retry_at_ns = now_ns + self.attempt * NS
        return self.progress("retry")

    def resume(self, identity: tuple[str, str, str], now_ns: int) -> None:
        if identity != self.identity:
            self.received = 0
            self.stopped = True
            raise BlockedEvidence("partial_revision_changed")
        if self.stopped or self.verified or self.retry_at_ns is None or now_ns < self.retry_at_ns:
            raise BlockedEvidence("retry_not_ready")
        self.attempt += 1
        self.retry_at_ns = None
        self.last_progress_ns = now_ns

    def verify(self, verified_size: int, verified_sha256: str, now_ns: int) -> TransferProgress:
        self.check(now_ns)
        if (self.received, verified_size, verified_sha256) != (
            self.asset.size,
            self.asset.size,
            self.asset.sha256,
        ):
            self.stopped = True
            raise BlockedEvidence("transfer_integrity")
        self.verified = True
        return self.progress("verified")
