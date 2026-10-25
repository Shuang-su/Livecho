"""Filesystem tests persist only original ordinary text, never weights or audio."""

import asyncio
import hashlib
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import pytest

from tools.asr_benchmark.contracts import Asset, PreparationManifest
from tools.asr_benchmark.model_cache import Identity, ModelCacheEntry, ModelOnlyCache
from tools.asr_benchmark.preparation import PreparationTransfer
from tools.asr_benchmark.runtime import BlockedEvidence

from .factories import preparation

# An independently written notice double. No asset is downloaded or model data generated.
NOTICE = b"Livecho metadata-only cache test notice. No model or audio data.\n"


def manifest() -> PreparationManifest:
    original = preparation()
    notice = Asset(
        path="NOTICE.txt",
        kind="notice",
        size=len(NOTICE),
        sha256=hashlib.sha256(NOTICE).hexdigest(),
    )
    assets = (*original.source_assets[:-1], notice)
    return PreparationManifest.model_validate(
        original.model_copy(
            update={
                "source_assets": assets,
                "mirrors": tuple(m.model_copy(update={"assets": assets}) for m in original.mirrors),
            }
        ).model_dump()
    )


def transfer() -> PreparationTransfer:
    return PreparationTransfer(manifest(), "huggingface", "NOTICE.txt", 0)


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[ModelOnlyCache]:
    with ModelOnlyCache(
        tmp_path.resolve() / "cache", tmp_path / "repo", manifest(), "huggingface"
    ) as value:
        yield value


def path(tmp_path: Path, suffix: str) -> Path:
    key = hashlib.sha256("|".join(transfer().identity).encode("ascii")).hexdigest()
    return tmp_path / "cache" / f"{key}.{suffix}"


def complete(entry: ModelCacheEntry) -> Identity:
    entry.append_model_chunk(NOTICE, 0)
    assert entry.inspect_partial(entry.identity) == (
        len(NOTICE),
        hashlib.sha256(NOTICE).hexdigest(),
    )
    return entry.identity


def test_resume_from_actual_file_and_atomic_promotion(
    cache: ModelOnlyCache, tmp_path: Path
) -> None:
    first = transfer()
    with cache.entry(first.identity) as entry:
        entry.append_model_chunk(NOTICE[:10], 0)
        first.advance(entry.offset(), 1)
        entry.save_checkpoint(first.checkpoint())
    # Normal close deliberately preserves an interrupted transfer; attempt bounds survive.
    second = transfer()
    with cache.entry(second.identity) as entry:
        second.restore_checkpoint(entry.load_checkpoint(), 2)
        assert entry.offset() == 10
        second.resume(second.identity, 1_000_000_002)
        entry.append_model_chunk(NOTICE[10:], entry.offset())
        second.advance(entry.offset(), 1_000_000_003)
        result = second.promote(entry, 1_000_000_004)
        assert result.outcome == "verified" and second.promoted
    assert path(tmp_path, "asset").read_bytes() == NOTICE
    assert not path(tmp_path, "partial").exists()
    assert not path(tmp_path, "checkpoint").exists()


def test_second_controller_is_nonblocking_and_close_releases_lock(cache: ModelOnlyCache) -> None:
    identity = transfer().identity
    with cache.entry(identity), pytest.raises(BlockedEvidence, match="cache_lock_unavailable"):
        cache.entry(identity)
    with cache.entry(identity) as entry:
        assert entry.offset() == 0


@pytest.mark.parametrize("kind", ["overwrite", "truncate", "append", "swap", "hardlink"])
def test_changed_verified_file_refuses_promotion(
    cache: ModelOnlyCache,
    tmp_path: Path,
    kind: str,
) -> None:
    with cache.entry(transfer().identity) as entry:
        identity = complete(entry)
        partial = path(tmp_path, "partial")
        if kind == "overwrite":
            with partial.open("r+b") as stream:
                stream.write(b"different text")
        elif kind == "truncate":
            with partial.open("r+b") as stream:
                stream.truncate(5)
        elif kind == "append":
            with partial.open("ab") as stream:
                stream.write(b"extra text")
        elif kind == "swap":
            partial.unlink()
            partial.write_bytes(NOTICE)
            partial.chmod(0o600)
        else:
            os.link(partial, tmp_path / "extra-link")
        with pytest.raises(BlockedEvidence, match="cache_promotion_failed"):
            entry.atomic_promote(identity)
    assert not path(tmp_path, "asset").exists()
    assert not partial.exists()


@pytest.mark.parametrize("kind", ["wrong_digest", "short", "oversize"])
def test_integrity_failure_invalidates_partial(
    cache: ModelOnlyCache,
    tmp_path: Path,
    kind: str,
) -> None:
    with cache.entry(transfer().identity) as entry:
        text = NOTICE[:-1] if kind == "short" else NOTICE
        entry.append_model_chunk(text, 0)
        if kind == "wrong_digest":
            path(tmp_path, "partial").write_bytes(b"X" * len(NOTICE))
        elif kind == "oversize":
            with path(tmp_path, "partial").open("ab") as stream:
                stream.write(b"extra notice")
        with pytest.raises(BlockedEvidence, match="cache_integrity"):
            entry.inspect_partial(entry.identity)
    assert not path(tmp_path, "partial").exists()


def test_hash_reader_is_bounded_under_growth(
    cache: ModelOnlyCache,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_read = os.read
    reads: list[int] = []
    with cache.entry(transfer().identity) as entry:
        entry.append_model_chunk(NOTICE, 0)

        def read(fd: int, amount: int) -> bytes:
            reads.append(amount)
            with path(tmp_path, "partial").open("ab") as stream:
                stream.write(b"additional text")
            return real_read(fd, amount)

        monkeypatch.setattr(os, "read", read)
        with pytest.raises(BlockedEvidence, match="cache_integrity"):
            entry.inspect_partial(entry.identity)
    assert reads == [len(NOTICE), 1]


@pytest.mark.parametrize("suffix", ["lock", "partial", "checkpoint"])
@pytest.mark.parametrize("kind", ["symlink", "hardlink", "fifo"])
def test_nonprivate_or_nonregular_files_rejected_without_touching_target(
    cache: ModelOnlyCache,
    tmp_path: Path,
    suffix: str,
    kind: str,
) -> None:
    target = tmp_path / "other-notice"
    target.write_bytes(NOTICE)
    target.chmod(0o600)
    name = path(tmp_path, suffix)
    if kind == "symlink":
        name.symlink_to(target)
    elif kind == "hardlink":
        os.link(target, name)
    else:
        os.mkfifo(name, 0o600)
    with pytest.raises(BlockedEvidence), cache.entry(transfer().identity) as entry:
        if suffix == "partial":
            entry.offset()
        elif suffix == "checkpoint":
            entry.load_checkpoint()
    assert target.read_bytes() == NOTICE


@pytest.mark.parametrize("kind", ["inside_repo", "git_file", "git_dir", "symlink", "public"])
def test_cache_root_rejects_git_and_unsafe_paths(tmp_path: Path, kind: str) -> None:
    base = tmp_path.resolve()
    repository = base / "repo"
    repository.mkdir()
    root = base / "cache"
    if kind == "inside_repo":
        root = repository / "cache"
    elif kind in {"git_file", "git_dir"}:
        external = base / "another-worktree"
        external.mkdir()
        if kind == "git_file":
            (external / ".git").write_text("gitdir: metadata-only\n")
        else:
            (external / ".git").mkdir()
        root = external / "cache"
    elif kind == "symlink":
        actual = base / "private-cache"
        actual.mkdir(mode=0o700)
        root.symlink_to(actual)
    else:
        root.mkdir(mode=0o755)
    with pytest.raises(BlockedEvidence):
        ModelOnlyCache(root, repository, manifest(), "huggingface")


def test_directory_descriptor_survives_path_substitution(
    cache: ModelOnlyCache, tmp_path: Path
) -> None:
    moved = tmp_path / "original-cache"
    (tmp_path / "cache").rename(moved)
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    (tmp_path / "cache").symlink_to(decoy)
    with cache.entry(transfer().identity) as entry:
        identity = complete(entry)
        entry.atomic_promote(identity)
    assert len(list(moved.glob("*.asset"))) == 1
    assert list(decoy.iterdir()) == []


def test_symlink_ancestor_is_rejected(tmp_path: Path) -> None:
    target = tmp_path.resolve() / "actual-parent"
    target.mkdir()
    alias = tmp_path.resolve() / "alias-parent"
    alias.symlink_to(target)
    with pytest.raises(BlockedEvidence, match="cache_root_unsafe"):
        ModelOnlyCache(alias / "cache", tmp_path / "repo", manifest(), "huggingface")
    assert list(target.iterdir()) == []


@pytest.mark.parametrize(
    "offset,chunk", [(True, NOTICE), (-1, NOTICE), (0, b""), (1, NOTICE), (0, NOTICE + b"extra")]
)
def test_bounds_reject_before_file_creation(
    cache: ModelOnlyCache,
    tmp_path: Path,
    offset: int,
    chunk: bytes,
) -> None:
    with (
        cache.entry(transfer().identity) as entry,
        pytest.raises(BlockedEvidence, match="cache_chunk_bounds"),
    ):
        entry.append_model_chunk(chunk, offset)
    assert not path(tmp_path, "partial").exists()


def test_stale_actual_offset_invalidates(cache: ModelOnlyCache, tmp_path: Path) -> None:
    with cache.entry(transfer().identity) as entry:
        entry.append_model_chunk(NOTICE[:5], 0)
        with pytest.raises(BlockedEvidence, match="cache_write_failed"):
            entry.append_model_chunk(NOTICE[5:], 4)
    assert not path(tmp_path, "partial").exists()


def test_checkpoint_identity_and_actual_length_must_match(cache: ModelOnlyCache) -> None:
    control = transfer()
    with cache.entry(control.identity) as entry:
        entry.append_model_chunk(NOTICE[:5], 0)
        with pytest.raises(BlockedEvidence, match="checkpoint_offset"):
            entry.save_checkpoint(control.checkpoint())
        control.advance(5, 1)
        entry.save_checkpoint(control.checkpoint())
        entry.append_model_chunk(NOTICE[5:6], 5)
        with pytest.raises(BlockedEvidence, match="checkpoint_invalid"):
            entry.load_checkpoint()
        changed = control.checkpoint().replace(control.identity[0], "f" * 64)
        with pytest.raises(BlockedEvidence, match="checkpoint_identity"):
            entry.save_checkpoint(changed)
    with pytest.raises(BlockedEvidence, match="cache_identity_denied"):
        cache.entry(("f" * 64, *control.identity[1:]))


@pytest.mark.parametrize("kind", ["file", "symlink", "hardlink"])
def test_existing_final_preserved(cache: ModelOnlyCache, tmp_path: Path, kind: str) -> None:
    with cache.entry(transfer().identity) as entry:
        identity = complete(entry)
        target = tmp_path / "previous-notice"
        target.write_text("previous complete notice")
        if kind == "symlink":
            path(tmp_path, "asset").symlink_to(target)
        elif kind == "hardlink":
            os.link(target, path(tmp_path, "asset"))
        else:
            path(tmp_path, "asset").write_text("previous complete notice")
        with pytest.raises(BlockedEvidence, match="cache_promotion_failed"):
            entry.atomic_promote(identity)
    assert path(tmp_path, "asset").read_text() == "previous complete notice"
    assert target.read_text() == "previous complete notice"


def test_replace_failure_cannot_leave_verified_partial(
    cache: ModelOnlyCache,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with cache.entry(transfer().identity) as entry:
        identity = complete(entry)

        def fail(src: str, dst: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
            raise OSError("test-only replace failure")

        monkeypatch.setattr(os, "replace", fail)
        with pytest.raises(BlockedEvidence, match="cache_promotion_failed"):
            entry.atomic_promote(identity)
    assert not path(tmp_path, "partial").exists()
    assert not path(tmp_path, "asset").exists()
    with cache.entry(transfer().identity):
        pass


def test_checkpoint_sync_failure_removes_both_versions(
    cache: ModelOnlyCache,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = transfer()
    with cache.entry(control.identity) as entry:
        entry.save_checkpoint(control.checkpoint())

        def fail(fd: int) -> None:
            raise asyncio.CancelledError

        monkeypatch.setattr(os, "fsync", fail)
        with pytest.raises(BlockedEvidence, match="checkpoint_write_failed"):
            entry.save_checkpoint(control.checkpoint())
    assert not path(tmp_path, "checkpoint").exists()
    assert not path(tmp_path, "checkpoint-new").exists()


@pytest.mark.parametrize("stage", ["write", "promote", "directory_sync"])
def test_cancellation_or_sync_failure_invalidates_and_releases_lock(
    cache: ModelOnlyCache,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    real_fsync = os.fsync
    with pytest.raises(BlockedEvidence), cache.entry(transfer().identity) as entry:
        if stage != "write":
            identity = complete(entry)
        calls = 0

        def fail(fd: int) -> None:
            nonlocal calls
            calls += 1
            if stage != "directory_sync" or calls == 2:
                raise asyncio.CancelledError
            real_fsync(fd)

        monkeypatch.setattr(os, "fsync", fail)
        if stage == "write":
            entry.append_model_chunk(NOTICE, 0)
        else:
            entry.atomic_promote(identity)
    assert not path(tmp_path, "partial").exists()
    assert not path(tmp_path, "asset").exists()
    with cache.entry(transfer().identity):
        pass


def test_cancelled_context_releases_lock_and_discards_partial(
    cache: ModelOnlyCache, tmp_path: Path
) -> None:
    with pytest.raises(asyncio.CancelledError), cache.entry(transfer().identity) as entry:
        entry.append_model_chunk(NOTICE[:5], 0)
        raise asyncio.CancelledError
    assert not path(tmp_path, "partial").exists()
    with cache.entry(transfer().identity):
        pass


def test_cleanup_attempts_all_files_when_unlink_fails(
    cache: ModelOnlyCache,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_unlink = os.unlink
    attempted: list[str] = []
    with cache.entry(transfer().identity) as entry:
        entry.append_model_chunk(NOTICE[:5], 0)

        def unlink(name: str, *, dir_fd: int | None = None) -> None:
            attempted.append(name)
            if name.endswith(".partial"):
                raise asyncio.CancelledError
            real_unlink(name, dir_fd=dir_fd)

        with monkeypatch.context() as patch:
            patch.setattr(os, "unlink", unlink)
            with pytest.raises(BlockedEvidence, match="cache_invalidation_failed"):
                entry.invalidate_partial(entry.identity)
    assert [name.rsplit(".", 1)[1] for name in attempted] == [
        "partial",
        "checkpoint",
        "checkpoint-new",
    ]
    assert entry.closed
    with cache.entry(transfer().identity):
        pass


@pytest.mark.parametrize("mode", ["huggingface", "modelscope"])
def test_mirror_checkpoint_identity_is_bound(
    tmp_path: Path, mode: Literal["huggingface", "modelscope"]
) -> None:
    with ModelOnlyCache(tmp_path.resolve() / "cache", tmp_path / "repo", manifest(), mode) as cache:
        control = transfer()
        with cache.entry(control.identity) as entry:
            if mode == "huggingface":
                entry.save_checkpoint(control.checkpoint())
            else:
                with pytest.raises(BlockedEvidence, match="checkpoint_identity"):
                    entry.save_checkpoint(control.checkpoint())
