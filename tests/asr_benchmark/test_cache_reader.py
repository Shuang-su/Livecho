"""Only original ordinary notice text is persisted; no weights or audio are created."""

import asyncio
import hashlib
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal

import pytest

from tools.asr_benchmark.cache_reader import FinalModelCache, VerifiedModelReader
from tools.asr_benchmark.cold_load import local_model_load
from tools.asr_benchmark.contracts import MODELS, NS, Asset, InferenceManifest
from tools.asr_benchmark.model_cache import ModelCacheEntry
from tools.asr_benchmark.runtime import BlockedEvidence

from .factories import inference, preparation

NOTICES = (
    b"Original ordinary text double A. No model data.\n",
    b"Original ordinary text double B. No model data.\n",
)


def manifest() -> InferenceManifest:
    base = inference(MODELS[0])
    # Labels satisfy the complete manifest contract; all stored contents are notices,
    # never encoded tensors/tokenizers/configs or executable model assets.
    assets = tuple(
        asset.model_copy(
            update={
                "size": len(NOTICES[index % 2]),
                "sha256": hashlib.sha256(NOTICES[index % 2]).hexdigest(),
            }
        )
        for index, asset in enumerate(base.converted_assets)
    )
    return InferenceManifest.model_validate(
        base.model_copy(
            update={
                "converted_assets": assets,
            }
        ).model_dump()
    )


def asset_path(tmp_path: Path, asset: Asset, final: InferenceManifest | None = None) -> Path:
    final = final or manifest()
    identity = (final.preparation_sha256, final.source_revision, asset.sha256)
    key = hashlib.sha256("|".join(identity).encode("ascii")).hexdigest()
    return tmp_path / "cache" / f"{key}.asset"


def populate(tmp_path: Path) -> None:
    (tmp_path / "cache").mkdir(mode=0o700)
    for index, asset in enumerate(manifest().converted_assets):
        file = asset_path(tmp_path, asset)
        file.write_bytes(NOTICES[index % 2])
        file.chmod(0o600)


def cache(tmp_path: Path, final: InferenceManifest | None = None) -> FinalModelCache:
    return FinalModelCache(
        tmp_path.resolve() / "cache", tmp_path / "repo", preparation(), final or manifest()
    )


class Backend:
    def __init__(self) -> None:
        self.provider_revision = manifest().provider_revision
        self.dependency_lock_sha256 = manifest().dependency_lock_sha256
        self.unloaded = True
        self.closed = False
        self.initialized = 0
        self.synchronized = 0
        self.retained: Mapping[str, VerifiedModelReader] = {}
        self.on_initialize: Callable[[], None] = lambda: None
        self.on_sync: Callable[[], None] = lambda: None
        self.on_close: Callable[[], None] = lambda: None

    def initialize(
        self,
        manifest: InferenceManifest,
        assets: Mapping[str, VerifiedModelReader],
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> None:
        assert local_files_only is True and trust_remote_code is False
        assert set(assets) == {a.path for a in manifest.converted_assets}
        self.initialized += 1
        self.retained = assets
        for index, asset in enumerate(manifest.converted_assets):
            assert assets[asset.path].read_at(0, asset.size) == NOTICES[index % 2]
        self.on_initialize()
        self.unloaded = False

    def synchronize(self) -> None:
        self.synchronized += 1
        self.on_sync()

    def close(self) -> None:
        self.closed = True
        self.on_close()


class Guard:
    def execute(self, operation: Callable[[], None], deadline_ns: int) -> None:
        assert deadline_ns == 100 + 30 * NS
        operation()


def test_verified_aliases_share_lock_and_reads_are_scoped(tmp_path: Path) -> None:
    populate(tmp_path)
    with cache(tmp_path) as owner:
        readers = owner.open_assets(lambda: False)
        assert len(readers) == 4 and len(set(readers.values())) == 2
        for index, asset in enumerate(manifest().converted_assets):
            reader = readers[asset.path]
            assert reader.read_at(3, 8) == NOTICES[index % 2][3:11]
            assert reader.read_at(reader.size, 0) == b""
            assert not hasattr(reader, "fileno") and not hasattr(reader, "path")
        with pytest.raises(BlockedEvidence, match="cache_reader_unavailable"):
            owner.open_assets(lambda: False)
    for reader in readers.values():
        with pytest.raises(BlockedEvidence, match="cache_read_failed"):
            reader.read_at(0, 1)
    owner.close()


def test_local_load_closes_readers_before_yield_and_backend_on_exit(tmp_path: Path) -> None:
    populate(tmp_path)
    backend = Backend()
    times = iter((100, 900))
    with local_model_load(
        cache(tmp_path), backend, clock=lambda: next(times), guard=Guard(), cancelled=lambda: False
    ) as observation:
        assert (observation.load_start_ns, observation.ready_ns) == (100, 900)
        assert backend.initialized == backend.synchronized == 1
        assert not backend.closed
        for reader in backend.retained.values():
            with pytest.raises(BlockedEvidence, match="cache_read_failed"):
                reader.read_at(0, 1)
    assert backend.closed


@pytest.mark.parametrize(
    "kind", ["missing", "partial_only", "short", "corrupt", "symlink", "hardlink", "fifo"]
)
def test_all_final_assets_verify_before_any_backend_call(tmp_path: Path, kind: str) -> None:
    populate(tmp_path)
    target = asset_path(tmp_path, manifest().converted_assets[1])
    target.unlink()
    if kind == "partial_only":
        target.with_suffix(".partial").write_bytes(NOTICES[1])
    elif kind in {"short", "corrupt"}:
        target.write_bytes(NOTICES[1][:2] if kind == "short" else b"x" * len(NOTICES[1]))
        target.chmod(0o600)
    elif kind in {"symlink", "hardlink"}:
        outside = tmp_path / "other-notice"
        outside.write_bytes(NOTICES[1])
        outside.chmod(0o600)
        if kind == "symlink":
            target.symlink_to(outside)
        else:
            os.link(outside, target)
    elif kind == "fifo":
        os.mkfifo(target, 0o600)
    backend = Backend()
    with (
        pytest.raises(BlockedEvidence, match="cache_final_set_invalid"),
        local_model_load(
            cache(tmp_path),
            backend,
            clock=lambda: 100,
            guard=Guard(),
            cancelled=lambda: False,
        ),
    ):
        pytest.fail("invalid asset set became ready")
    assert backend.initialized == 0 and backend.closed
    # Failure released all earlier locks, even when a later asset failed.
    first = manifest().converted_assets[0]
    identity = (manifest().preparation_sha256, manifest().source_revision, first.sha256)
    directory = os.open(tmp_path / "cache", os.O_RDONLY | os.O_DIRECTORY)
    try:
        with ModelCacheEntry(directory, identity, first, "huggingface"):
            pass
    finally:
        os.close(directory)


@pytest.mark.parametrize(
    "field",
    ["preparation_sha256", "source_revision", "tensor_map_sha256", "dependency_lock_sha256"],
)
def test_final_binding_mismatch_fails_before_cache_open(tmp_path: Path, field: str) -> None:
    value = "f" * (40 if field == "source_revision" else 64)
    final = manifest().model_copy(update={field: value})
    with pytest.raises(BlockedEvidence, match="inference_preparation_mismatch"):
        cache(tmp_path, final)
    assert not (tmp_path / "cache").exists()


def test_preparation_files_cannot_substitute_for_converted_files(tmp_path: Path) -> None:
    (tmp_path / "cache").mkdir(mode=0o700)
    for source in preparation().source_assets:
        asset_path(tmp_path, source).write_bytes(NOTICES[0])
    with cache(tmp_path) as owner, pytest.raises(BlockedEvidence, match="cache_final_set_invalid"):
        owner.open_assets(lambda: False)


def test_same_digest_with_inconsistent_lengths_is_denied(tmp_path: Path) -> None:
    final = manifest()
    assets = list(final.converted_assets)
    assets[2] = assets[2].model_copy(update={"size": assets[2].size + 1})
    changed = final.model_copy(update={"converted_assets": tuple(assets)})
    with pytest.raises(BlockedEvidence, match="cache_asset_identity"):
        cache(tmp_path, changed)


@pytest.mark.parametrize(
    "offset,count", [(True, 1), (0, True), (-1, 1), (0, -1), (0, 1024**2 + 1), (100, 0), (1, 999)]
)
def test_read_bounds_reject_without_io(
    tmp_path: Path, offset: int, count: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    populate(tmp_path)
    with cache(tmp_path) as owner:
        reader = next(iter(owner.open_assets(lambda: False).values()))

        def no_read(fd: int, size: int, position: int) -> bytes:
            pytest.fail("invalid read reached the filesystem")

        monkeypatch.setattr(os, "pread", no_read)
        with pytest.raises(BlockedEvidence, match="cache_read_bounds"):
            reader.read_at(offset, count)


@pytest.mark.parametrize("kind", ["overwrite", "restore_mtime", "truncate", "append", "swap"])
def test_postverification_mutation_invalidates_reader(tmp_path: Path, kind: str) -> None:
    populate(tmp_path)
    asset = manifest().converted_assets[0]
    file = asset_path(tmp_path, asset)
    with cache(tmp_path) as owner:
        reader = owner.open_assets(lambda: False)[asset.path]
        old = file.stat()
        if kind in {"overwrite", "restore_mtime"}:
            file.write_bytes(b"x" * asset.size)
            if kind == "restore_mtime":
                os.utime(file, ns=(old.st_atime_ns, old.st_mtime_ns))
        elif kind == "truncate":
            file.write_text("short ordinary text")
        elif kind == "append":
            with file.open("ab") as stream:
                stream.write(b"extra notice text")
        else:
            file.unlink()
            file.write_bytes(NOTICES[0])
            file.chmod(0o600)
        with pytest.raises(BlockedEvidence, match="cache_read_failed"):
            reader.read_at(0, 1)
        assert reader.closed


def test_second_reader_conflicts_until_first_closes(tmp_path: Path) -> None:
    populate(tmp_path)
    with cache(tmp_path) as first:
        first.open_assets(lambda: False)
        with (
            cache(tmp_path) as second,
            pytest.raises(BlockedEvidence, match="cache_final_set_invalid"),
        ):
            second.open_assets(lambda: False)
    with cache(tmp_path) as replacement:
        replacement.open_assets(lambda: False)


@pytest.mark.parametrize("field", ["provider_revision", "dependency_lock_sha256", "unloaded"])
def test_backend_pins_and_unloaded_state_required(tmp_path: Path, field: str) -> None:
    populate(tmp_path)
    backend = Backend()
    setattr(backend, field, False if field == "unloaded" else "wrong")
    with (
        pytest.raises(BlockedEvidence, match="load_backend_mismatch"),
        local_model_load(
            cache(tmp_path),
            backend,
            clock=lambda: 100,
            guard=Guard(),
            cancelled=lambda: False,
        ),
    ):
        pytest.fail("unready backend admitted")
    assert backend.initialized == 0 and backend.closed


@pytest.mark.parametrize("stage", ["initialize", "sync", "clock", "caller", "close", "cancel"])
def test_failures_cleanup_readers_and_backend(tmp_path: Path, stage: str) -> None:
    populate(tmp_path)
    backend = Backend()
    cancelled = False
    ticks = iter((100, 200))

    def fail() -> None:
        raise asyncio.CancelledError

    def cancel() -> None:
        nonlocal cancelled
        cancelled = True

    if stage == "initialize":
        backend.on_initialize = fail
    elif stage == "sync":
        backend.on_sync = fail
    elif stage == "close":
        backend.on_close = fail
    elif stage == "cancel":
        backend.on_initialize = cancel

    def clock() -> int:
        if stage == "clock":
            raise asyncio.CancelledError
        return next(ticks)

    with (
        pytest.raises(BlockedEvidence),
        local_model_load(
            cache(tmp_path),
            backend,
            clock=clock,
            guard=Guard(),
            cancelled=lambda: cancelled,
        ),
    ):
        if stage == "caller":
            fail()
    assert backend.closed
    assert all(reader.closed for reader in backend.retained.values())
    with cache(tmp_path) as replacement:
        replacement.open_assets(lambda: False)


@pytest.mark.parametrize("ready", [True, 99, 30 * NS + 101])
def test_timing_failures_never_yield_ready(tmp_path: Path, ready: int) -> None:
    populate(tmp_path)
    backend = Backend()
    ticks = iter((100, ready))
    with (
        pytest.raises(BlockedEvidence, match="load_timing"),
        local_model_load(
            cache(tmp_path),
            backend,
            clock=lambda: next(ticks),
            guard=Guard(),
            cancelled=lambda: False,
        ),
    ):
        pytest.fail("invalid timing yielded readiness")
    assert backend.closed


def test_mutation_during_sync_fails_before_readiness(tmp_path: Path) -> None:
    populate(tmp_path)
    backend = Backend()

    def mutate() -> None:
        asset_path(tmp_path, manifest().converted_assets[0]).write_text("changed notice")

    backend.on_sync = mutate
    with (
        pytest.raises(BlockedEvidence),
        local_model_load(
            cache(tmp_path),
            backend,
            clock=lambda: 100,
            guard=Guard(),
            cancelled=lambda: False,
        ),
    ):
        pytest.fail("changed assets yielded readiness")
    assert backend.closed


def test_skipped_guard_operation_cannot_manufacture_ready(tmp_path: Path) -> None:
    populate(tmp_path)

    class SkippingGuard:
        def execute(self, operation: Callable[[], None], deadline_ns: int) -> None:
            pass

    backend = Backend()
    with (
        pytest.raises(BlockedEvidence, match="load_not_ready"),
        local_model_load(
            cache(tmp_path),
            backend,
            clock=lambda: 100,
            guard=SkippingGuard(),
            cancelled=lambda: False,
        ),
    ):
        pytest.fail("skipped initialization yielded readiness")
    assert backend.closed


def test_close_cancellation_still_closes_other_readers_and_locks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    populate(tmp_path)
    owner = cache(tmp_path)
    readers = owner.open_assets(lambda: False)
    real_close = os.close
    closed: list[int] = []

    def close(fd: int) -> None:
        real_close(fd)
        closed.append(fd)
        if len(closed) == 1:
            raise asyncio.CancelledError

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", close)
        with pytest.raises(BlockedEvidence, match="cache_final_close_failed"):
            owner.close()
    assert len(closed) == 7  # two readers, each asset/lock/directory, plus owner directory
    assert len(set(closed)) == 7 and all(reader.closed for reader in readers.values())
    owner.close()
    with cache(tmp_path) as replacement:
        replacement.open_assets(lambda: False)


def test_cancelled_verification_releases_handles(tmp_path: Path) -> None:
    populate(tmp_path)
    with cache(tmp_path) as owner, pytest.raises(BlockedEvidence, match="cache_final_set_invalid"):
        owner.open_assets(lambda: True)
    with cache(tmp_path) as replacement:
        replacement.open_assets(lambda: False)


def test_final_read_does_not_create_missing_root(tmp_path: Path) -> None:
    with pytest.raises(BlockedEvidence, match="cache_final_root_invalid"):
        cache(tmp_path)
    assert not (tmp_path / "cache").exists()


def test_backend_individual_alias_close_invalidates_load(tmp_path: Path) -> None:
    populate(tmp_path)
    backend = Backend()

    def close_alias() -> None:
        first, _, alias, _ = manifest().converted_assets
        assert backend.retained[first.path] is backend.retained[alias.path]
        backend.retained[first.path].close()
        assert backend.retained[alias.path].closed

    backend.on_initialize = close_alias
    with (
        pytest.raises(BlockedEvidence),
        local_model_load(
            cache(tmp_path),
            backend,
            clock=lambda: 100,
            guard=Guard(),
            cancelled=lambda: False,
        ),
    ):
        pytest.fail("individually closed borrowed asset yielded readiness")
    assert backend.closed


def test_mutation_during_read_prevents_returning_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    populate(tmp_path)
    real_pread = os.pread
    asset = manifest().converted_assets[0]
    with cache(tmp_path) as owner:
        reader = owner.open_assets(lambda: False)[asset.path]

        def pread(fd: int, count: int, offset: int) -> bytes:
            data = real_pread(fd, count, offset)
            asset_path(tmp_path, asset).write_text("mutated ordinary notice")
            return data

        monkeypatch.setattr(os, "pread", pread)
        with pytest.raises(BlockedEvidence, match="cache_read_failed"):
            reader.read_at(0, 4)
        assert reader.closed


def test_hash_verification_stops_at_manifest_size_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    populate(tmp_path)
    first = min(manifest().converted_assets, key=lambda asset: asset.sha256)
    real_pread = os.pread
    counts: list[int] = []

    def grow(fd: int, count: int, offset: int) -> bytes:
        counts.append(count)
        with asset_path(tmp_path, first).open("ab") as stream:
            stream.write(b"extra ordinary text")
        return real_pread(fd, count, offset)

    monkeypatch.setattr(os, "pread", grow)
    with cache(tmp_path) as owner, pytest.raises(BlockedEvidence, match="cache_final_set_invalid"):
        owner.open_assets(lambda: False)
    assert counts == [first.size, 1]


def test_asset_descriptors_are_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    populate(tmp_path)
    real_open = os.open
    modes: list[int] = []

    def open_file(name: str, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        if name.endswith(".asset"):
            modes.append(flags & os.O_ACCMODE)
        return real_open(name, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", open_file)
    with cache(tmp_path) as owner:
        owner.open_assets(lambda: False)
    assert modes == [os.O_RDONLY, os.O_RDONLY]
