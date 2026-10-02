"""Model-only transfer control plane, tested using metadata doubles.

The transport and asset writer are intentionally not installed: immutable source
manifests, conversion/provider pins and approvals are still missing. No arbitrary URL,
path, body, request header or server diagnostic is accepted by this control plane.
"""

from dataclasses import dataclass
from typing import Literal

from .contracts import NS, Asset, PreparationManifest, metadata_digest
from .runtime import BlockedEvidence


@dataclass(frozen=True)
class TransferProgress:
    asset_label: str
    received: int
    total: int
    percent: float
    retry_count: int
    outcome: Literal["partial", "retry", "verified", "stopped"]


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
        self.identity = (metadata_digest(manifest), mirrors[0].revision, self.asset.sha256)
        self.received = 0
        self.last_progress_ns = now_ns
        self.attempt = 1
        self.retry_at_ns: int | None = None
        self.stopped = False
        self.verified = False

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
