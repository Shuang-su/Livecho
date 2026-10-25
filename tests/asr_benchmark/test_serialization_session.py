"""Original ordinary text filesystem I/O and opaque tokens; no real serializer."""

import asyncio
import gc
import os
import weakref
from collections.abc import Callable, Iterator, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any, Literal

import pytest

from tools.asr_benchmark import serialization_session as module
from tools.asr_benchmark.contracts import PreparationManifest, metadata_digest
from tools.asr_benchmark.conversion import ConvertedTensor
from tools.asr_benchmark.converted_store import (
    ConversionReceipt,
    ConversionStaging,
    OutputPlan,
    read_conversion_receipt,
)
from tools.asr_benchmark.model_cache import ModelOnlyCache
from tools.asr_benchmark.runtime import BlockedEvidence
from tools.asr_benchmark.serialization_session import (
    ModelInput,
    OutputWriter,
    prepare_converted_artifacts,
)
from tools.asr_benchmark.source_cache import VerifiedSourceAssets

from .test_conversion_session import Backend, Token, assert_released, manifest, populate
from .test_converted_store import TEXTS
from .test_converted_store import plan as storage_plan
from .test_source_preparation import content


def plan() -> OutputPlan:
    return OutputPlan.model_validate(
        storage_plan()
        .model_copy(update={"preparation_sha256": metadata_digest(manifest())})
        .model_dump()
    )


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[ModelOnlyCache]:
    with ModelOnlyCache(
        tmp_path / "sources", tmp_path / "repo", manifest(), "huggingface"
    ) as value:
        populate(value)
        yield value


class Serializer:
    def __init__(self) -> None:
        self.converter_revision = manifest().converter_revision
        self.dependency_lock_sha256 = manifest().dependency_lock_sha256
        self.fresh = True
        self.close_calls = self.serialize_calls = 0
        self.on_event: Callable[[str], None] = lambda event: None
        self.converted: Mapping[str, ConvertedTensor[Token]] = {}
        self.auxiliary: Mapping[str, ModelInput] = {}
        self.input: ModelInput | None = None
        self.writer: OutputWriter | None = None
        self.iterator: Iterator[str] | None = None
        self.emit: Callable[[OutputWriter, OutputPlan], None] = self.normal_emit

    @staticmethod
    def normal_emit(writer: OutputWriter, output_plan: OutputPlan) -> None:
        for spec, text in zip(output_plan.outputs, TEXTS, strict=True):
            writer.write_output(spec.path, (text[:5], text[5:]))

    def serialize(
        self,
        preparation: PreparationManifest,
        output_plan: OutputPlan,
        converted: Mapping[str, ConvertedTensor[Token]],
        auxiliary: Mapping[str, ModelInput],
        outputs: OutputWriter,
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> None:
        self.serialize_calls += 1
        assert local_files_only is True and trust_remote_code is False
        assert preparation == manifest() and output_plan == plan()
        assert set(converted) == {rule.name for rule in preparation.tensor_map}
        assert converted[preparation.tensor_map[0].name].weight.label == "packed"
        assert converted["retained_vector"].weight.label == "retained_vector"
        expected = {
            asset.path: asset for asset in preparation.source_assets if asset.kind != "weights"
        }
        assert set(auxiliary) == set(expected)
        for name, reader in auxiliary.items():
            assert reader.size == expected[name].size
            assert reader.read_at(0, reader.size) == content(expected[name])
            assert not any(hasattr(reader, name) for name in ("path", "fileno", "close", "write"))
        assert not any(hasattr(outputs, name) for name in ("commit", "close", "path", "fileno"))
        self.converted, self.auxiliary, self.writer = converted, auxiliary, outputs
        self.iterator = iter(converted)
        next(self.iterator)
        self.input = next(iter(auxiliary.values()))
        self.on_event("before")
        self.emit(outputs, output_plan)
        self.fresh = False
        self.on_event("after")

    def close(self) -> None:
        self.close_calls += 1
        self.on_event("close")


def run(
    tmp_path: Path,
    cache: ModelOnlyCache,
    backend: Backend,
    serializer: Serializer,
    **kwargs: Any,
) -> ConversionReceipt:
    return asyncio.run(
        prepare_converted_artifacts(
            manifest(),
            "huggingface",
            cache,
            backend,
            serializer,
            kwargs.pop("plan", plan()),
            tmp_path / "outputs",
            tmp_path / "repo",
            **kwargs,
        )
    )


def reopened(tmp_path: Path) -> ConversionReceipt:
    return read_conversion_receipt(tmp_path / "outputs", tmp_path / "repo", manifest(), plan())


def assert_cleanup(
    tmp_path: Path, cache: ModelOnlyCache, backend: Backend, serializer: Serializer
) -> None:
    assert backend.events.count("close") == 1
    assert serializer.close_calls == 1
    assert all(reader.closed for reader in backend.readers.values())
    assert_released(cache)
    assert not list((tmp_path / "outputs").glob("*.stage"))


def assert_no_receipt(tmp_path: Path) -> None:
    assert not list((tmp_path / "outputs").glob("*.receipt"))


def test_success_cleanup_precedes_commit_and_all_public_borrows_expire(
    tmp_path: Path, cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, serializer = Backend(), Serializer()
    events: list[str] = []
    backend.on_event = lambda name: events.append("converter:" + name)
    serializer.on_event = lambda name: events.append("serializer:" + name)
    original = ConversionStaging.commit

    def commit(store: ConversionStaging) -> ConversionReceipt:
        assert backend.closed and serializer.close_calls == 1
        assert_released(cache)
        events.append("commit")
        return original(store)

    monkeypatch.setattr(ConversionStaging, "commit", commit)
    receipt = run(tmp_path, cache, backend, serializer)
    assert events[-4:] == ["serializer:after", "serializer:close", "converter:close", "commit"]
    assert receipt == reopened(tmp_path) and receipt.status == "unapproved"
    assert not hasattr(receipt, "approval")
    assert (
        serializer.input is not None
        and serializer.iterator is not None
        and serializer.writer is not None
    )
    with pytest.raises(BlockedEvidence, match="serialization_borrow_closed"):
        len(serializer.converted)
    with pytest.raises(BlockedEvidence, match="serialization_borrow_closed"):
        next(serializer.iterator)
    with pytest.raises(BlockedEvidence, match="serialization_borrow_closed"):
        serializer.input.read_at(0, 1)
    with pytest.raises(BlockedEvidence, match="serialization_borrow_closed"):
        _ = serializer.input.size
    with pytest.raises(BlockedEvidence, match="serialization_borrow_closed"):
        serializer.writer.write_output(plan().outputs[0].path, (TEXTS[0],))
    assert_cleanup(tmp_path, cache, backend, serializer)


@pytest.mark.parametrize(
    "bad",
    [
        "converter_pin",
        "converter_lock",
        "converter_state",
        "serializer_pin",
        "serializer_lock",
        "serializer_state",
        "plan",
        "plan_shape",
        "cache",
        "cancel",
    ],
)
def test_failed_admission_does_no_work_and_leaves_caller_ownership(
    tmp_path: Path, cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    backend, serializer = Backend(), Serializer()
    output_plan = plan()
    if bad == "converter_pin":
        backend.converter_revision = "different"
    elif bad == "converter_lock":
        backend.dependency_lock_sha256 = "different"
    elif bad == "converter_state":
        backend._unloaded = False
    elif bad == "serializer_pin":
        serializer.converter_revision = "different"
    elif bad == "serializer_lock":
        serializer.dependency_lock_sha256 = "different"
    elif bad == "serializer_state":
        serializer.fresh = 1  # type: ignore[assignment]
    elif bad == "plan":
        output_plan = output_plan.model_copy(update={"converter_revision": "f" * 40})
    elif bad == "plan_shape":
        output_plan = output_plan.model_copy(update={"max_total_bytes": True})
    elif bad == "cache":
        cache.close()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("I/O reached before admission")

    monkeypatch.setattr(module, "ConversionStaging", forbidden)
    monkeypatch.setattr(module, "_probe_local", forbidden)
    with pytest.raises(asyncio.CancelledError if bad == "cancel" else BlockedEvidence):
        run(
            tmp_path,
            cache,
            backend,
            serializer,
            plan=output_plan,
            cancelled=lambda: bad == "cancel",
        )
    assert backend.events == [] and serializer.serialize_calls == serializer.close_calls == 0
    assert not (tmp_path / "outputs").exists()


@pytest.mark.parametrize(
    "failure", ["stage", "inner_admission", "missing", "corrupt", "conversion"]
)
def test_admitted_failures_close_both_backends_once(
    tmp_path: Path, cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    backend, serializer = Backend(), Serializer()
    if failure == "stage":

        def unavailable(*args: Any, **kwargs: Any) -> Any:
            raise OSError("private output location")

        monkeypatch.setattr(module, "ConversionStaging", unavailable)
    elif failure == "inner_admission":
        original = module._probe_local

        def probe(guard: Any) -> None:
            original(guard)
            backend._unloaded = False

        monkeypatch.setattr(module, "_probe_local", probe)
    elif failure in {"missing", "corrupt"}:
        path = next((tmp_path / "sources").glob("*.asset"))
        if failure == "missing":
            path.unlink()
        else:
            path.write_bytes(b"X" + path.read_bytes()[1:])
    else:

        def fail(name: str) -> None:
            if name == "quantize":
                raise OSError("private converter diagnostic")

        backend.on_event = fail
    with pytest.raises(BlockedEvidence):
        run(tmp_path, cache, backend, serializer)
    assert serializer.serialize_calls == 0
    if failure != "conversion":
        assert backend.events == ["close"]
    assert_cleanup(tmp_path, cache, backend, serializer)
    assert_no_receipt(tmp_path)


@pytest.mark.parametrize(
    "failure",
    ["missing", "unknown", "duplicate", "bounds", "iterator", "serialize", "fresh", "return_value"],
)
def test_serializer_and_output_failures_never_commit(
    tmp_path: Path, cache: ModelOnlyCache, failure: str
) -> None:
    backend, serializer = Backend(), Serializer()

    def emit(writer: OutputWriter, output_plan: OutputPlan) -> None:
        first = output_plan.outputs[0].path
        if failure == "missing":
            return
        if failure == "unknown":
            writer.write_output("extra.txt", (TEXTS[0],))
        elif failure == "duplicate":
            writer.write_output(first, (TEXTS[0],))
            writer.write_output(first, (TEXTS[0],))
        elif failure == "bounds":
            writer.write_output(first, (TEXTS[0] + b"!",))
        elif failure == "iterator":

            def chunks() -> Iterator[bytes]:
                yield TEXTS[0][:5]
                raise OSError("private iterator diagnostic")

            writer.write_output(first, chunks())
        else:
            serializer.normal_emit(writer, output_plan)

    serializer.emit = emit
    if failure == "serialize":

        def fail(event: str) -> None:
            if event == "after":
                raise RuntimeError("private serializer diagnostic")

        serializer.on_event = fail
    elif failure == "fresh":
        serializer.on_event = (
            lambda event: setattr(serializer, "fresh", 0) if event == "after" else None
        )
    elif failure == "return_value":
        original = serializer.serialize

        def wrong(*args: Any, **kwargs: Any) -> object:
            original(*args, **kwargs)
            return object()

        serializer.serialize = wrong  # type: ignore[assignment]
    with pytest.raises(BlockedEvidence) as error:
        run(tmp_path, cache, backend, serializer)
    assert "private" not in str(error.value)
    assert_cleanup(tmp_path, cache, backend, serializer)
    assert_no_receipt(tmp_path)


@pytest.mark.parametrize("caught", ["unknown", "pin", "cancel", "iterator"])
def test_swallowed_failure_is_sticky(tmp_path: Path, cache: ModelOnlyCache, caught: str) -> None:
    backend, serializer = Backend(), Serializer()
    cancel = False

    def emit(writer: OutputWriter, output_plan: OutputPlan) -> None:
        nonlocal cancel
        original_pin = serializer.converter_revision
        try:
            if caught == "pin":
                serializer.converter_revision = "changed"
            elif caught == "cancel":
                cancel = True

            def chunks() -> Iterator[bytes]:
                if caught == "iterator":
                    raise RuntimeError("original iterator fault")
                yield TEXTS[0]

            writer.write_output(
                "unknown.txt" if caught == "unknown" else output_plan.outputs[0].path, chunks()
            )
        except BaseException:
            pass  # Deliberately hostile control double: swallowing must not authorize commit.
        serializer.converter_revision = original_pin
        cancel = False

    serializer.emit = emit
    with pytest.raises(asyncio.CancelledError if caught == "cancel" else BlockedEvidence):
        run(tmp_path, cache, backend, serializer, cancelled=lambda: cancel)
    assert_cleanup(tmp_path, cache, backend, serializer)
    assert_no_receipt(tmp_path)


@pytest.mark.parametrize(
    "failure",
    ["source_close", "serializer_close", "converter_close", "both_close", "reader_change"],
)
def test_cleanup_failure_attempts_all_owners_and_never_commits(
    tmp_path: Path, cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    backend, serializer = Backend(), Serializer()
    if failure == "source_close":
        original = VerifiedSourceAssets.close
        closed = 0

        def close(owner: VerifiedSourceAssets) -> None:
            nonlocal closed
            original(owner)
            closed += 1
            if closed == 3:
                raise OSError("injected serializer-source close failure")

        monkeypatch.setattr(VerifiedSourceAssets, "close", close)
    if failure in {"serializer_close", "both_close"}:

        def serializer_fail(event: str) -> None:
            if event == "close":
                raise OSError("injected serializer close failure")

        serializer.on_event = serializer_fail
    if failure in {"converter_close", "both_close"}:

        def converter_fail(event: str) -> None:
            if event == "close":
                raise OSError("injected converter close failure")

        backend.on_event = converter_fail
    if failure == "reader_change":

        def mutate(event: str) -> None:
            if event == "after":
                path = next((tmp_path / "sources").glob("*.asset"))
                path.write_bytes(b"X" + path.read_bytes()[1:])

        serializer.on_event = mutate
    with pytest.raises(BlockedEvidence):
        run(tmp_path, cache, backend, serializer)
    assert_cleanup(tmp_path, cache, backend, serializer)
    assert_no_receipt(tmp_path)


@pytest.mark.parametrize(
    "when",
    [
        "before",
        "after",
        "source_close",
        "serializer_close",
        "converter_close",
        "receipt",
        "store_close",
    ],
)
def test_cancellation_before_delivery_respects_publication_boundary(
    tmp_path: Path, cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch, when: str
) -> None:
    backend, serializer = Backend(), Serializer()
    cancel = False

    def changed() -> None:
        nonlocal cancel
        cancel = True

    serializer.on_event = (
        lambda event: changed()
        if event == when or (event == "close" and when == "serializer_close")
        else None
    )
    backend.on_event = (
        lambda event: changed() if event == "close" and when == "converter_close" else None
    )
    if when == "source_close":
        original_source = VerifiedSourceAssets.close
        count = 0

        def source_close(owner: VerifiedSourceAssets) -> None:
            nonlocal count
            original_source(owner)
            count += 1
            if count == 3:
                changed()

        monkeypatch.setattr(VerifiedSourceAssets, "close", source_close)
    elif when == "receipt":
        original_rename = os.rename

        def rename(src: str, dst: str, **kwargs: Any) -> None:
            original_rename(src, dst, **kwargs)
            if dst.endswith(".receipt"):
                changed()

        monkeypatch.setattr(os, "rename", rename)
    elif when == "store_close":
        original_close = ConversionStaging.close

        def store_close(store: ConversionStaging) -> None:
            original_close(store)
            changed()

        monkeypatch.setattr(ConversionStaging, "close", store_close)
    with pytest.raises(asyncio.CancelledError):
        run(tmp_path, cache, backend, serializer, cancelled=lambda: cancel)
    monkeypatch.undo()
    assert_cleanup(tmp_path, cache, backend, serializer)
    if when in {"receipt", "store_close"}:
        assert reopened(tmp_path).status == "unapproved"
    else:
        assert_no_receipt(tmp_path)


def test_postcommit_storage_close_error_preserves_receipt_but_no_success(
    tmp_path: Path, cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, serializer = Backend(), Serializer()
    original = ConversionStaging.close

    def close(store: ConversionStaging) -> None:
        original(store)
        raise OSError("injected close after commit")

    monkeypatch.setattr(ConversionStaging, "close", close)
    with pytest.raises(BlockedEvidence, match="serialization_failed"):
        run(tmp_path, cache, backend, serializer)
    monkeypatch.undo()
    assert reopened(tmp_path).status == "unapproved"
    assert_cleanup(tmp_path, cache, backend, serializer)


def test_retained_aux_borrow_is_unavailable_inside_serializer_close(
    tmp_path: Path, cache: ModelOnlyCache
) -> None:
    backend, serializer = Backend(), Serializer()
    attempted = False

    def close_read(event: str) -> None:
        nonlocal attempted
        if event == "close":
            assert serializer.input is not None
            with pytest.raises(BlockedEvidence, match="serialization_borrow_closed"):
                serializer.input.read_at(0, 1)
            attempted = True

    serializer.on_event = close_read
    with pytest.raises(BlockedEvidence, match="serialization_failed"):
        run(tmp_path, cache, backend, serializer)
    assert attempted
    assert_cleanup(tmp_path, cache, backend, serializer)
    assert_no_receipt(tmp_path)


def test_pending_task_cancel_blocks_even_local_only_admission(
    tmp_path: Path, cache: ModelOnlyCache
) -> None:
    backend, serializer = Backend(), Serializer()

    async def exercise() -> None:
        task = asyncio.current_task()
        assert task is not None
        task.cancel()
        with suppress(asyncio.CancelledError):
            await asyncio.sleep(0)
        with pytest.raises(asyncio.CancelledError):
            await prepare_converted_artifacts(
                manifest(),
                "huggingface",
                cache,
                backend,
                serializer,
                plan(),
                tmp_path / "outputs",
                tmp_path / "repo",
            )
        task.uncancel()

    asyncio.run(exercise())
    assert backend.events == [] and serializer.close_calls == 0


@pytest.mark.parametrize("failure", ["success", "stage", "conversion", "close"])
def test_same_object_in_both_backend_roles_closes_once(
    tmp_path: Path, cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    class Shared(Backend, Serializer):
        def __init__(self) -> None:
            Backend.__init__(self)
            Serializer.__init__(self)

        def close(self) -> None:
            self.close_calls += 1
            Backend.close(self)
            if failure == "close":
                raise OSError("shared close failure")

    backend = Shared()
    if failure == "stage":

        def fail_stage(*args: Any, **kwargs: Any) -> Any:
            raise OSError("stage failure")

        monkeypatch.setattr(module, "ConversionStaging", fail_stage)
    elif failure == "conversion":

        def fail_conversion(event: str) -> None:
            if event == "quantize":
                raise OSError("conversion failure")

        backend.on_event = fail_conversion
    if failure == "success":
        assert run(tmp_path, cache, backend, backend) == reopened(tmp_path)
    else:
        with pytest.raises(BlockedEvidence):
            run(tmp_path, cache, backend, backend)
        assert_no_receipt(tmp_path)
    assert_cleanup(tmp_path, cache, backend, backend)


def test_bad_return_does_not_remain_in_owned_traceback_frame(
    tmp_path: Path, cache: ModelOnlyCache
) -> None:
    held: list[weakref.ReferenceType[Token]] = []

    class BadReturn(Serializer):
        def __init__(self) -> None:
            super().__init__()
            self.bad: Token | None = None

        def serialize(self, *args: Any, **kwargs: Any) -> None:
            super().serialize(*args, **kwargs)
            self.bad = Token("unexpected serializer return")
            held.append(weakref.ref(self.bad))
            return self.bad  # type: ignore[return-value]

        def close(self) -> None:
            self.bad = None
            super().close()

    backend, serializer = Backend(), BadReturn()
    with pytest.raises(BlockedEvidence, match="serialization_backend_state") as retained_error:
        run(tmp_path, cache, backend, serializer)
    gc.collect()
    assert retained_error.value.__traceback__ is not None
    assert held and held[0]() is None
    assert_cleanup(tmp_path, cache, backend, serializer)
    assert_no_receipt(tmp_path)


@pytest.mark.parametrize("stage", ["load", "quantize"])
def test_fresh_state_drift_during_conversion_rejected_before_serializer(
    tmp_path: Path, cache: ModelOnlyCache, stage: str
) -> None:
    backend, serializer = Backend(), Serializer()
    backend.on_event = lambda event: setattr(serializer, "fresh", False) if event == stage else None
    with pytest.raises(BlockedEvidence, match="serialization_backend_not_fresh"):
        run(tmp_path, cache, backend, serializer)
    assert serializer.serialize_calls == 0
    assert_cleanup(tmp_path, cache, backend, serializer)
    assert_no_receipt(tmp_path)


def test_auxiliary_reopen_never_downloads_missing_local_input(
    tmp_path: Path, cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend, serializer = Backend(), Serializer()

    def remove(event: str) -> None:
        if event == "quantize":
            next((tmp_path / "sources").glob("*.asset")).unlink()

    def forbidden() -> Any:
        raise AssertionError("auxiliary reopen requested a transfer")

    backend.on_event = remove
    monkeypatch.setattr(module, "_no_download", forbidden)
    with pytest.raises(BlockedEvidence, match="source_collection_incomplete"):
        run(tmp_path, cache, backend, serializer)
    assert serializer.serialize_calls == 0
    assert_cleanup(tmp_path, cache, backend, serializer)
    assert_no_receipt(tmp_path)
