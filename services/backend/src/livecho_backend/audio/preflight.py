"""No evidence is inferred from a local FFmpeg installation or point-in-time RSS/swap."""

from __future__ import annotations

import hashlib
import os
import resource
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .contracts import AudioError, Reason, SourceFormat
from .ledger import DECODER_LIMIT, NONCANONICAL_LIMIT, PROCESS_LIMIT

PIPE_CAPACITY = 4096


@dataclass(frozen=True, slots=True)
class AllocationInventory:
    """Exact reviewed upper bounds, including both full kernel pipe capacities."""

    decoder_audio_bytes: int
    parent_noncanonical_bytes: int
    parent_canonical_bytes: int
    stdin_capacity: int
    stdout_capacity: int
    evidence_id: str

    def validate(self) -> None:
        if (
            not self.evidence_id
            or not 2 * PIPE_CAPACITY <= self.decoder_audio_bytes <= DECODER_LIMIT
            or not 2 * PIPE_CAPACITY <= self.parent_noncanonical_bytes <= NONCANONICAL_LIMIT
            or not 64_000 <= self.parent_canonical_bytes <= 960_000
            or self.parent_canonical_bytes + self.parent_noncanonical_bytes > PROCESS_LIMIT
            or self.stdin_capacity != PIPE_CAPACITY
            or self.stdout_capacity != PIPE_CAPACITY
        ):
            raise AudioError(Reason.BUDGET_UNVERIFIED)


@dataclass(frozen=True, slots=True)
class ApprovedBuild:
    identity: str
    path: Path
    executable_sha256: str
    version_line: str
    license_evidence: str
    dependency_evidence: str
    inventory: AllocationInventory


@dataclass(frozen=True, slots=True)
class ApprovedHost:
    identity: str
    platform: str
    machine_boot_id: str
    no_paging_evidence: str
    no_crash_collection_evidence: str
    process_tree_evidence: str


# Owner-reviewed records must be added by a later evidence-bearing change. No public
# argument, environment variable, CLI option, or caller-provided boolean can fill these.
APPROVED_BUILDS: tuple[ApprovedBuild, ...] = ()
APPROVED_HOSTS: tuple[ApprovedHost, ...] = ()
_CAPABILITY_KEY = object()


class RuntimePermit:
    def __init__(self, key: object, build: ApprovedBuild, host: ApprovedHost) -> None:
        if key is not _CAPABILITY_KEY:
            raise AudioError(Reason.BUDGET_UNVERIFIED)
        self.build = build
        self.host = host
        self._pid = os.getpid()

    def require(self) -> None:
        if (
            self._pid != os.getpid()
            or self.build not in APPROVED_BUILDS
            or self.host not in APPROVED_HOSTS
        ):
            raise AudioError(Reason.BUDGET_UNVERIFIED)


def fixed_arguments(build: ApprovedBuild, source_format: SourceFormat) -> tuple[str, ...]:
    """Only trusted build configuration supplies a path; no shell or source options."""
    return (
        str(build.path),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "quiet",
        "-nostats",
        "-threads",
        "1",
        "-filter_threads",
        "1",
        "-protocol_whitelist",
        "pipe",
        "-f",
        "s16le",
        "-ar",
        str(source_format.sample_rate_hz),
        "-ac",
        str(source_format.channels),
        "-c:a",
        "pcm_s16le",
        "-blocksize",
        "4096",
        "-i",
        "pipe:0",
        "-map",
        "0:a:0",
        "-vn",
        "-sn",
        "-dn",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "s16le",
        "-protocol_whitelist",
        "pipe",
        "-blocksize",
        "4096",
        "pipe:1",
    )


def preflight(build_id: str, host_id: str) -> RuntimePermit:
    build = next((item for item in APPROVED_BUILDS if item.identity == build_id), None)
    host = next((item for item in APPROVED_HOSTS if item.identity == host_id), None)
    if build is None or host is None:
        raise AudioError(Reason.BUDGET_UNVERIFIED)
    build.inventory.validate()
    if (
        sys.platform != "linux"
        or host.platform != sys.platform
        or not all((build.license_evidence, build.dependency_evidence))
        or not all(
            (host.no_paging_evidence, host.no_crash_collection_evidence, host.process_tree_evidence)
        )
    ):
        raise AudioError(Reason.BUDGET_UNVERIFIED)
    try:
        if Path("/proc/sys/kernel/random/boot_id").read_text().strip() != host.machine_boot_id:
            raise AudioError(Reason.BUDGET_UNVERIFIED)
        if not build.path.is_absolute() or build.path.is_symlink():
            raise AudioError(Reason.BUDGET_UNVERIFIED)
        mode = build.path.stat().st_mode
        if not stat.S_ISREG(mode) or mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise AudioError(Reason.BUDGET_UNVERIFIED)
        # Hash the executable only. No audio value is ever hashed.
        with build.path.open("rb") as executable:
            digest = hashlib.file_digest(executable, "sha256").hexdigest()
        if digest != build.executable_sha256:
            raise AudioError(Reason.BUDGET_UNVERIFIED)
        result = subprocess.run(
            [str(build.path), "-version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2,
            env={"LANG": "C"},
        )
        if result.returncode != 0 or result.stdout.splitlines()[0].decode() != build.version_line:
            raise AudioError(Reason.BUDGET_UNVERIFIED)
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        raise AudioError(Reason.BUDGET_UNVERIFIED) from None
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if resource.getrlimit(resource.RLIMIT_CORE) != (0, 0):
            raise AudioError(Reason.BUDGET_UNVERIFIED)
    except (OSError, ValueError):
        raise AudioError(Reason.BUDGET_UNVERIFIED) from None
    return RuntimePermit(_CAPABILITY_KEY, build, host)


def main() -> int:
    # This reports the checked-in gate, never probes arbitrary local executables.
    if not APPROVED_BUILDS or not APPROVED_HOSTS:
        print("audio_budget_unverified: approved FFmpeg inventory and host evidence are pending")
        return 2
    print("Trusted runtime checks require the approved host invocation recorded in evidence.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
