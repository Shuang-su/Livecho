"""Original ordinary text only; no model/tensor/audio or real serializer execution."""

import asyncio
import hashlib
import os
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tools.asr_benchmark import converted_store as module
from tools.asr_benchmark.cache_reader import FinalModelCache
from tools.asr_benchmark.contracts import MODELS, Asset, InferenceManifest, metadata_digest
from tools.asr_benchmark.converted_store import (
    CHUNK_BYTES,
    ConversionStaging,
    OutputPlan,
    OutputSpec,
    read_conversion_receipt,
)
from tools.asr_benchmark.model_cache import ModelCacheEntry
from tools.asr_benchmark.runtime import BlockedEvidence

from .factories import inference, preparation

TEXTS = (
    b"Original storage notice alpha. No tensor data.\n",
    b"Original storage notice beta. No tokenizer data.\n",
    b"Original storage notice alpha. No tensor data.\n",
    b"Original storage notice gamma. No model data.\n",
)
PATHS = ("weights.safetensors", "tokenizer.json", "config.json", "NOTICE.txt")
KINDS = ("weights", "tokenizer", "config", "notice")


def plan() -> OutputPlan:
    source = preparation()
    return OutputPlan(
        preparation_sha256=metadata_digest(source),
        converter_revision=source.converter_revision,
        dependency_lock_sha256=source.dependency_lock_sha256,
        outputs=tuple(
            OutputSpec(path=path, kind=kind, max_bytes=len(text))  # type: ignore[arg-type]
            for path, kind, text in zip(PATHS, KINDS, TEXTS, strict=True)
        ),
        max_total_bytes=sum(map(len, TEXTS)),
    )


def owner(tmp_path: Path, **kwargs: Any) -> ConversionStaging:
    return ConversionStaging(
        tmp_path / "cache", tmp_path / "repo", preparation(), kwargs.pop("plan", plan()), **kwargs
    )


def write_all(store: ConversionStaging, texts: tuple[bytes, ...] = TEXTS) -> None:
    for path, text in zip(PATHS, texts, strict=True):
        with store.open_output(path) as sink:
            sink.write(text[:8])
            sink.write(text[8:])


def read(tmp_path: Path) -> module.ConversionReceipt:
    return read_conversion_receipt(tmp_path / "cache", tmp_path / "repo", preparation(), plan())


def path_for(tmp_path: Path, asset: Asset) -> Path:
    identity = (plan().preparation_sha256, preparation().source_revision, asset.sha256)
    key = hashlib.sha256("|".join(identity).encode("ascii")).hexdigest()
    return tmp_path / "cache" / f"{key}.asset"


def assert_released(tmp_path: Path) -> None:
    assert not list((tmp_path / "cache").glob("*.stage"))
    with owner(tmp_path):
        pass


def test_actual_receipt_aliases_idempotence_and_independent_final_manifest(tmp_path: Path) -> None:
    with owner(tmp_path) as store:
        write_all(store)
        receipt = store.commit()
        assert receipt.status == "unapproved"
        assert not hasattr(receipt, "approval") and not hasattr(receipt, "converted_assets")
        assert [(a.path, a.size, a.sha256) for a in receipt.outputs] == [
            (path, len(text), hashlib.sha256(text).hexdigest())
            for path, text in zip(PATHS, TEXTS, strict=True)
        ]
        with pytest.raises(BlockedEvidence):
            store.commit()
    assert len(list((tmp_path / "cache").glob("*.asset"))) == 3
    assert read(tmp_path) == receipt
    stamps = {path: path.stat() for path in (tmp_path / "cache").glob("*.asset")}
    with owner(tmp_path) as retry:
        write_all(retry)
        assert retry.commit() == receipt
    assert {path: path.stat() for path in stamps} == stamps
    # Independent test-only final metadata is supplied explicitly, not minted by storage.
    final = InferenceManifest.model_validate(
        inference(MODELS[0]).model_copy(update={"converted_assets": receipt.outputs}).model_dump()
    )
    with FinalModelCache(tmp_path / "cache", tmp_path / "repo", preparation(), final) as cache:
        readers = cache.open_assets(lambda: False)
        assert readers[PATHS[0]] is readers[PATHS[2]]
        for asset, text in zip(receipt.outputs, TEXTS, strict=True):
            assert readers[asset.path].read_at(0, asset.size) == text
    with pytest.raises(BlockedEvidence, match="inference_preparation_mismatch"):
        FinalModelCache(tmp_path / "cache", tmp_path / "repo", preparation(), receipt)  # type: ignore[arg-type]
    assert_released(tmp_path)


@pytest.mark.parametrize(
    "field", ["preparation_sha256", "converter_revision", "dependency_lock_sha256"]
)
def test_wrong_binding_and_forged_plan_make_no_cache(tmp_path: Path, field: str) -> None:
    wrong = plan().model_copy(update={field: "f" * (40 if field == "converter_revision" else 64)})
    with pytest.raises(BlockedEvidence, match="conversion_plan_binding"):
        owner(tmp_path, plan=wrong)
    assert not (tmp_path / "cache").exists()
    with pytest.raises(BlockedEvidence):
        owner(tmp_path, plan=plan().model_copy(update={"max_total_bytes": True}))
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize(
    "path", ["../file.txt", "/file.txt", ".hidden.txt", "file.wav", "a//b.txt"]
)
def test_closed_model_paths(path: str) -> None:
    with pytest.raises(ValidationError):
        OutputSpec(path=path, kind="notice", max_bytes=1)


@pytest.mark.parametrize(
    "update",
    [
        {"outputs": ()},
        {"outputs": (plan().outputs[0],) * 4},
        {"outputs": plan().outputs[:-1]},
        {"max_total_bytes": 0},
        {"max_total_bytes": 128 * 1024**3 + 1},
        {"outputs": plan().outputs * 65},
    ],
)
def test_closed_inventory_and_caps(update: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        OutputPlan.model_validate(plan().model_copy(update=update).model_dump())
    with pytest.raises(ValidationError):
        OutputSpec(path="file.txt", kind="notice", max_bytes=64 * 1024**3 + 1)


@pytest.mark.parametrize("fault", ["unknown", "duplicate", "empty", "missing", "nested"])
def test_inventory_failure_never_commits(tmp_path: Path, fault: str) -> None:
    with owner(tmp_path) as store:
        with pytest.raises(BlockedEvidence):
            if fault == "unknown":
                with store.open_output("unknown.txt"):
                    pass
            elif fault == "duplicate":
                write_all(store)
                with store.open_output(PATHS[0]):
                    pass
            elif fault == "empty":
                with store.open_output(PATHS[0]):
                    pass
            elif fault == "nested":
                with store.open_output(PATHS[0]), store.open_output(PATHS[1]):
                    pass
            else:
                store.commit()
        with pytest.raises(BlockedEvidence):
            store.commit()
    assert not list((tmp_path / "cache").glob("*.receipt"))
    assert_released(tmp_path)


@pytest.mark.parametrize(
    "chunk", [b"", b"z" * (CHUNK_BYTES + 1), bytearray(b"text"), TEXTS[0] + b"!"]
)
def test_chunk_bounds_fail_before_append(tmp_path: Path, chunk: Any) -> None:
    with (
        owner(tmp_path) as store,
        pytest.raises(BlockedEvidence, match="conversion_output_bounds"),
        store.open_output(PATHS[0]) as sink,
    ):
        sink.write(chunk)
    assert_released(tmp_path)


def test_total_cap_counts_logical_alias_bytes(tmp_path: Path) -> None:
    smaller = plan().model_copy(update={"max_total_bytes": sum(map(len, TEXTS)) - 1})
    with (
        owner(tmp_path, plan=smaller) as store,
        pytest.raises(BlockedEvidence, match="conversion_output_bounds"),
    ):
        write_all(store)
    assert not list((tmp_path / "cache").glob("*.asset"))
    assert_released(tmp_path)


def test_borrowed_sink_revoked_and_single_writer(tmp_path: Path) -> None:
    with owner(tmp_path) as store:
        with store.open_output(PATHS[0]) as sink:
            sink.write(TEXTS[0])
        with pytest.raises(BlockedEvidence, match="conversion_sink_closed"):
            sink.write(b"ordinary text")
        with pytest.raises(BlockedEvidence, match="conversion_store_unavailable"):
            owner(tmp_path)
        fds = [
            store._stage,
            store._store.directory,
            store._store.lock,
            *[o.fd for o in store._outputs.values()],
        ]
    for fd in fds:
        with pytest.raises(OSError):
            os.fstat(fd)
    assert_released(tmp_path)


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "public"])
def test_lock_file_is_private_single_link_and_nofollow(tmp_path: Path, unsafe: str) -> None:
    root = tmp_path / "cache"
    root.mkdir(mode=0o700)
    target = tmp_path / "ordinary.txt"
    target.write_text("Original lock-test notice.")
    target.chmod(0o600)
    lock = root / f"conversion-{plan().preparation_sha256}.lock"
    if unsafe == "symlink":
        lock.symlink_to(target)
    elif unsafe == "hardlink":
        os.link(target, lock)
    else:
        lock.write_text("Original public lock notice.")
        lock.chmod(0o644)
    with pytest.raises(BlockedEvidence):
        owner(tmp_path)
    assert target.read_text() == "Original lock-test notice."
    assert not list(root.glob("*.stage"))


def test_cache_inside_git_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("Original git marker double")
    with pytest.raises(BlockedEvidence, match="cache_inside_git"):
        ConversionStaging(repo / "cache", repo, preparation(), plan())


@pytest.mark.parametrize("fault", ["write", "short", "hash", "sync"])
def test_io_failure_cleans_owned_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    with owner(tmp_path) as store:

        def fail(*args: Any, **kwargs: Any) -> Any:
            if fault in {"short", "hash"}:
                return 0 if fault == "short" else b""
            raise OSError("private path text must not escape")

        name = {"write": "write", "short": "write", "hash": "pread", "sync": "fsync"}[fault]
        monkeypatch.setattr(os, name, fail)
        with pytest.raises(BlockedEvidence) as error, store.open_output(PATHS[0]) as sink:
            sink.write(TEXTS[0])
        assert "private path" not in str(error.value)
        monkeypatch.undo()
    assert_released(tmp_path)


def test_short_writes_are_completed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = os.write

    def short(fd: int, data: Any) -> int:
        return original(fd, data[:3])

    monkeypatch.setattr(os, "write", short)
    with owner(tmp_path) as store:
        write_all(store)
        store.commit()
    assert read(tmp_path).outputs[0].sha256 == hashlib.sha256(TEXTS[0]).hexdigest()


@pytest.mark.parametrize("when", ["before_finish", "after_finish"])
def test_held_output_mutation_is_rejected(tmp_path: Path, when: str) -> None:
    with owner(tmp_path) as store, pytest.raises(BlockedEvidence):
        with store.open_output(PATHS[0]) as sink:
            sink.write(TEXTS[0])
            if when == "before_finish":
                os.pwrite(store._outputs[PATHS[0]].fd, b"X", 0)
        if when == "after_finish":
            os.pwrite(store._outputs[PATHS[0]].fd, b"X", 0)
            for path, text in zip(PATHS[1:], TEXTS[1:], strict=True):
                with store.open_output(path) as sink:
                    sink.write(text)
            store.commit()
    assert not list((tmp_path / "cache").glob("*.receipt"))
    assert_released(tmp_path)


@pytest.mark.parametrize("unsafe", ["corrupt", "symlink", "hardlink"])
def test_existing_asset_never_repaired_or_overwritten(tmp_path: Path, unsafe: str) -> None:
    with owner(tmp_path) as store:
        write_all(store)
        asset = store._outputs[PATHS[0]].asset
        assert asset is not None
        path = path_for(tmp_path, asset)
        target = tmp_path / "original.txt"
        target.write_bytes(TEXTS[0])
        target.chmod(0o600)
        if unsafe == "symlink":
            path.symlink_to(target)
        elif unsafe == "hardlink":
            os.link(target, path)
        else:
            path.write_bytes(b"X" + TEXTS[0][1:])
            path.chmod(0o600)
        before = path.lstat()
        with pytest.raises(BlockedEvidence):
            store.commit()
        assert path.lstat() == before
        assert target.read_bytes() == TEXTS[0]
    assert not list((tmp_path / "cache").glob("*.receipt"))
    assert_released(tmp_path)


def test_asset_lock_contention_blocks_receipt(tmp_path: Path) -> None:
    with owner(tmp_path) as store:
        write_all(store)
        asset = store._outputs[PATHS[0]].asset
        assert asset is not None
        with (
            ModelCacheEntry(
                store._store.directory,
                (plan().preparation_sha256, preparation().source_revision, asset.sha256),
                asset,
                "huggingface",
            ),
            pytest.raises(BlockedEvidence, match="cache_lock_unavailable"),
        ):
            store.commit()
    assert_released(tmp_path)


@pytest.mark.parametrize("point", ["asset", "before_receipt", "after_receipt", "directory_sync"])
def test_publish_faults_preserve_orphans_or_complete_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str
) -> None:
    original_rename, original_sync = os.rename, os.fsync
    receipt_renamed = False
    with owner(tmp_path) as store:
        write_all(store)

        def rename(src: str, dst: str, **kwargs: Any) -> None:
            nonlocal receipt_renamed
            if point == "before_receipt" and dst.endswith(".receipt"):
                raise OSError("before receipt")
            original_rename(src, dst, **kwargs)
            if dst.endswith(".receipt"):
                receipt_renamed = True
                if point == "after_receipt":
                    raise OSError("after receipt")
            elif point == "asset":
                raise OSError("after first asset")

        def sync(fd: int) -> None:
            if point == "directory_sync" and receipt_renamed and fd == store._store.directory:
                raise OSError("receipt visible, durability uncertain")
            original_sync(fd)

        monkeypatch.setattr(os, "rename", rename)
        monkeypatch.setattr(os, "fsync", sync)
        with pytest.raises(BlockedEvidence):
            store.commit()
        monkeypatch.undo()
    assert len(list((tmp_path / "cache").glob("*.asset"))) >= 1
    if receipt_renamed:
        assert len(read(tmp_path).outputs) == 4
    else:
        with pytest.raises(BlockedEvidence, match="conversion_receipt_missing"):
            read(tmp_path)
    preserved = {path: path.stat() for path in (tmp_path / "cache").glob("*.asset")}
    with owner(tmp_path) as retry:
        write_all(retry)
        retry.commit()
    assert read(tmp_path).status == "unapproved"
    assert {path: path.stat() for path in preserved} == preserved
    assert_released(tmp_path)


def test_conflicting_retry_preserves_original_complete_set(tmp_path: Path) -> None:
    with owner(tmp_path) as store:
        write_all(store)
        receipt = store.commit()
    before = {path: path.read_bytes() for path in (tmp_path / "cache").glob("*.asset")}
    with owner(tmp_path) as retry:
        changed = (b"X" + TEXTS[0][1:], *TEXTS[1:])
        write_all(retry, changed)
        with pytest.raises(BlockedEvidence, match="conversion_receipt_conflict"):
            retry.commit()
    assert read(tmp_path) == receipt
    assert {path: path.read_bytes() for path in (tmp_path / "cache").glob("*.asset")} == before


@pytest.mark.parametrize("when", ["admission", "write", "hash", "asset", "receipt"])
def test_cancellation_cleanup_at_io_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, when: str
) -> None:
    cancelled = when == "admission"
    original_write, original_read, original_rename = os.write, os.pread, os.rename

    def write(fd: int, data: Any) -> int:
        nonlocal cancelled
        result = original_write(fd, data)
        if when == "write":
            cancelled = True
        return result

    def pread(fd: int, count: int, offset: int) -> bytes:
        nonlocal cancelled
        result = original_read(fd, count, offset)
        if when == "hash":
            cancelled = True
        return result

    def rename(src: str, dst: str, **kwargs: Any) -> None:
        nonlocal cancelled
        original_rename(src, dst, **kwargs)
        if (when == "asset" and dst.endswith(".asset")) or (
            when == "receipt" and dst.endswith(".receipt")
        ):
            cancelled = True

    monkeypatch.setattr(os, "write", write)
    monkeypatch.setattr(os, "pread", pread)
    monkeypatch.setattr(os, "rename", rename)
    with (
        pytest.raises(asyncio.CancelledError),
        owner(tmp_path, cancelled=lambda: cancelled) as store,
    ):
        write_all(store)
        store.commit()
    monkeypatch.undo()
    if when == "admission":
        assert not (tmp_path / "cache").exists()
    else:
        assert_released(tmp_path)
        if when == "receipt":
            assert read(tmp_path).status == "unapproved"
        else:
            assert not list((tmp_path / "cache").glob("*.receipt"))


def test_pending_task_cancellation_denies_local_admission(tmp_path: Path) -> None:
    async def exercise() -> None:
        task = asyncio.current_task()
        assert task is not None
        task.cancel()
        with suppress(asyncio.CancelledError):
            await asyncio.sleep(0)
        with pytest.raises(asyncio.CancelledError):
            owner(tmp_path)
        task.uncancel()

    asyncio.run(exercise())
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("change", ["bytes", "missing", "receipt_extra", "receipt_inventory"])
def test_reopen_rehashes_all_outputs_and_strict_receipt(tmp_path: Path, change: str) -> None:
    with owner(tmp_path) as store:
        write_all(store)
        receipt = store.commit()
    if change == "bytes":
        path_for(tmp_path, receipt.outputs[-1]).write_bytes(b"X" + TEXTS[-1][1:])
    elif change == "missing":
        path_for(tmp_path, receipt.outputs[-1]).unlink()
    else:
        path = next((tmp_path / "cache").glob("*.receipt"))
        if change == "receipt_extra":
            text = receipt.model_dump_json()[:-1] + ',"approval":{}}'
        else:
            text = receipt.model_copy(update={"outputs": receipt.outputs[:-1]}).model_dump_json()
        path.write_text(text)
    with pytest.raises(BlockedEvidence):
        read(tmp_path)
    assert_released(tmp_path)


def test_orphan_stages_not_adopted_or_removed(tmp_path: Path) -> None:
    root = tmp_path / "cache"
    root.mkdir(mode=0o700)
    abandoned = root / "conversion-abandoned.stage"
    abandoned.mkdir(mode=0o700)
    original = abandoned / "ordinary.txt"
    original.write_text("Original abandoned model-only notice.")
    with owner(tmp_path) as store:
        write_all(store)
        store.commit()
    assert original.read_text() == "Original abandoned model-only notice."
    assert list(root.glob("*.stage")) == [abandoned]


def test_cleanup_preserves_foreign_substitution_and_releases_locks(tmp_path: Path) -> None:
    store = owner(tmp_path)
    with store.open_output(PATHS[0]) as sink:
        sink.write(TEXTS[0])
    stage = tmp_path / "cache" / store._stage_name
    original = stage / "0.output"
    original.rename(stage / "foreign-moved.txt")
    original.write_text("Original foreign replacement notice.")
    with pytest.raises(BlockedEvidence, match="conversion_stage_cleanup"):
        store.close()
    assert original.read_text() == "Original foreign replacement notice."
    assert (stage / "foreign-moved.txt").read_bytes() == TEXTS[0]
    with owner(tmp_path):
        pass


@pytest.mark.parametrize("which", ["create_stat", "second_stat", "stage_open"])
def test_constructor_and_open_failure_do_not_leak_owned_fds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, which: str
) -> None:
    original_open, original_stamp = os.open, module._named_stamp
    opened: list[int] = []
    seen = 0

    def tracked_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if which == "stage_open" and str(path).endswith(".stage"):
            raise OSError("injected directory open failure")
        result = original_open(path, flags, *args, **kwargs)
        opened.append(result)
        return result

    def stamp(directory: int, name: str, fd: int) -> module.Fingerprint:  # type: ignore[name-defined]
        nonlocal seen
        if name == "0.output":
            seen += 1
            if seen == (1 if which == "create_stat" else 2):
                raise OSError("injected file observation failure")
        return original_stamp(directory, name, fd)

    monkeypatch.setattr(os, "open", tracked_open)
    monkeypatch.setattr(module, "_named_stamp", stamp)
    with pytest.raises(BlockedEvidence), owner(tmp_path) as store, store.open_output(PATHS[0]):
        raise AssertionError("fault was not reached")
    monkeypatch.undo()
    for fd in set(opened):
        with pytest.raises(OSError):
            os.fstat(fd)
    assert_released(tmp_path)


def test_finished_file_same_length_mutation_with_mtime_restore_rejected(tmp_path: Path) -> None:
    with owner(tmp_path) as store:
        write_all(store)
        output = store._outputs[PATHS[0]]
        before = os.fstat(output.fd)
        os.pwrite(output.fd, b"X", 0)
        os.utime(output.fd, ns=(before.st_atime_ns, before.st_mtime_ns))
        with pytest.raises(BlockedEvidence, match="conversion_output_changed"):
            store.commit()
    assert not list((tmp_path / "cache").glob("*.receipt"))
    assert_released(tmp_path)


def test_finished_file_name_replacement_rejected_without_deleting_replacement(
    tmp_path: Path,
) -> None:
    store = owner(tmp_path)
    write_all(store)
    stage = tmp_path / "cache" / store._stage_name
    target = stage / "0.output"
    target.rename(stage / "foreign-moved.txt")
    target.write_bytes(TEXTS[0])
    target.chmod(0o600)
    with pytest.raises(BlockedEvidence, match="conversion_file_changed"):
        store.commit()
    with pytest.raises(BlockedEvidence, match="conversion_stage_cleanup"):
        store.close()
    assert target.read_bytes() == TEXTS[0]
    assert not list((tmp_path / "cache").glob("*.receipt"))
    with owner(tmp_path):
        pass


def test_close_failure_after_commit_preserves_complete_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = owner(tmp_path)
    write_all(store)
    receipt = store.commit()
    original = os.close
    doomed = store._outputs[PATHS[0]].fd

    def close(fd: int) -> None:
        original(fd)
        if fd == doomed:
            raise OSError("injected close failure after actual release")

    monkeypatch.setattr(os, "close", close)
    with pytest.raises(BlockedEvidence, match="conversion_stage_cleanup"):
        store.close()
    monkeypatch.undo()
    assert read(tmp_path) == receipt
    assert_released(tmp_path)


def test_canonical_namespace_ignores_different_modelscope_source_revision(tmp_path: Path) -> None:
    base = preparation()
    mirrors = tuple(
        mirror.model_copy(update={"revision": "f" * 40}) if mirror.mode == "modelscope" else mirror
        for mirror in base.mirrors
    )
    record = type(base).model_validate(base.model_copy(update={"mirrors": mirrors}).model_dump())
    output_plan = plan().model_copy(update={"preparation_sha256": metadata_digest(record)})
    with ConversionStaging(tmp_path / "cache", tmp_path / "repo", record, output_plan) as store:
        write_all(store)
        receipt = store.commit()
    assert receipt.source_revision == record.source_revision != mirrors[1].revision
    for asset in receipt.outputs:
        canonical = (metadata_digest(record), record.source_revision, asset.sha256)
        canonical_key = hashlib.sha256("|".join(canonical).encode("ascii")).hexdigest()
        assert (tmp_path / "cache" / f"{canonical_key}.asset").read_bytes() in TEXTS
        mirror = (metadata_digest(record), "f" * 40, asset.sha256)
        mirror_key = hashlib.sha256("|".join(mirror).encode("ascii")).hexdigest()
        assert not (tmp_path / "cache" / f"{mirror_key}.asset").exists()
    assert (
        read_conversion_receipt(tmp_path / "cache", tmp_path / "repo", record, output_plan)
        == receipt
    )


def test_forged_output_limit_is_revalidated_before_filesystem(tmp_path: Path) -> None:
    first = plan().outputs[0].model_copy(update={"max_bytes": -1})
    forged = plan().model_copy(update={"outputs": (first, *plan().outputs[1:])})
    with pytest.raises(BlockedEvidence):
        owner(tmp_path, plan=forged)
    assert not (tmp_path / "cache").exists()


def test_retry_does_not_repair_a_damaged_committed_set(tmp_path: Path) -> None:
    with owner(tmp_path) as store:
        write_all(store)
        receipt = store.commit()
    missing = path_for(tmp_path, receipt.outputs[-1])
    missing.unlink()
    with owner(tmp_path) as retry:
        write_all(retry)
        with pytest.raises(BlockedEvidence):
            retry.commit()
    assert not missing.exists()
    assert_released(tmp_path)


@pytest.mark.parametrize("append", [False, True])
def test_receipt_readback_rejects_mutation_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, append: bool
) -> None:
    original = os.fsync
    with owner(tmp_path) as store:
        write_all(store)

        def sync(fd: int) -> None:
            value = os.fstat(fd)
            if (value.st_dev, value.st_ino) == store._owned.get("receipt.new"):
                os.pwrite(fd, b"X", value.st_size if append else 0)
            original(fd)

        monkeypatch.setattr(os, "fsync", sync)
        with pytest.raises(BlockedEvidence, match="conversion_receipt_changed"):
            store.commit()
        monkeypatch.undo()
    assert not list((tmp_path / "cache").glob("*.receipt"))
    assert_released(tmp_path)
