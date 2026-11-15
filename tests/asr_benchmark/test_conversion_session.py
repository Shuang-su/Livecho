"""Preparation orchestration using original notice text and opaque tokens only."""

import asyncio
import gc
import hashlib
import weakref
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from tools.asr_benchmark import conversion_session as session_module
from tools.asr_benchmark.cache_reader import VerifiedModelReader
from tools.asr_benchmark.contracts import Asset, PreparationManifest, TensorRule, metadata_digest
from tools.asr_benchmark.conversion import (
    ConversionBackend,
    ConvertedTensor,
    TensorShape,
    convert_verified_tensors,
)
from tools.asr_benchmark.conversion_session import BorrowedConversion, conversion_session
from tools.asr_benchmark.model_cache import ModelOnlyCache
from tools.asr_benchmark.runtime import BlockedEvidence

from .test_source_preparation import content
from .test_source_preparation import manifest as source_manifest


def manifest() -> PreparationManifest:
    base = source_manifest()
    retained = TensorRule(
        name="retained_vector",
        source_dtype="float32",
        operation="retain",
        classification="unsupported",
    )
    return PreparationManifest.model_validate(
        base.model_copy(update={"tensor_map": (*base.tensor_map, retained)}).model_dump()
    )


def asset_identity(index: int) -> tuple[str, str, str]:
    record = manifest()
    return metadata_digest(record), record.source_revision, record.source_assets[index].sha256


def populate(cache: ModelOnlyCache) -> None:
    for index in (0, 1):
        asset = manifest().source_assets[index]
        with cache.entry(asset_identity(index)) as entry:
            entry.append_model_chunk(content(asset), 0)
            entry.inspect_partial(entry.identity)
            entry.atomic_promote(entry.identity)


def assert_released(cache: ModelOnlyCache) -> None:
    assert not cache.closed
    for index in (0, 1):
        with cache.entry(asset_identity(index)):
            pass


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[ModelOnlyCache]:
    with ModelOnlyCache(
        tmp_path.resolve() / "cache", tmp_path / "repo", manifest(), "huggingface"
    ) as cache:
        yield cache


@dataclass(frozen=True)
class Token:
    label: str


class Backend:
    def __init__(self) -> None:
        record = manifest()
        self.converter_revision = record.converter_revision
        self.dependency_lock_sha256 = record.dependency_lock_sha256
        self._unloaded = True
        self.closed = False
        self.events: list[str] = []
        self.readers: Mapping[str, VerifiedModelReader] = {}
        self.tokens = {rule.name: Token(rule.name) for rule in record.tensor_map}
        self.records = tuple(self.tokens.items())
        self.descriptions = {
            rule.name: TensorShape(
                rule=rule, shape=(128, 64) if rule.operation != "retain" else (7,)
            )
            for rule in record.tensor_map
        }
        self.on_event: Callable[[str], None] = lambda event: None
        self._evaluations = self._synchronizations = 0

    @property
    def unloaded(self) -> bool:
        return self._unloaded

    def event(self, name: str) -> None:
        self.events.append(name)
        self.on_event(name)

    def load_sources(
        self,
        record: PreparationManifest,
        assets: Mapping[str, VerifiedModelReader],
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> tuple[tuple[str, Token], ...]:
        self.readers = assets
        assert local_files_only is True and trust_remote_code is False
        assert set(assets) == {asset.path for asset in record.source_assets}
        for asset in record.source_assets:
            assert assets[asset.path].read_at(0, asset.size) == content(asset)
        self.event("load")
        self._unloaded = False
        return self.records

    def describe(self, name: str, token: Token) -> TensorShape:
        assert all(reader.closed for reader in self.readers.values())
        assert token is self.tokens[name]
        self.event("describe:" + name)
        return self.descriptions[name]

    def quantize(
        self, token: Token, *, group_size: int, bits: int, mode: str
    ) -> tuple[Token, Token, Token]:
        assert (group_size, bits, mode) == (64, 8, "affine")
        assert token is self.tokens[manifest().tensor_map[0].name]
        self.event("quantize")
        return Token("packed"), Token("scales"), Token("biases")

    def evaluate(self, tokens: tuple[Token, ...]) -> None:
        self._evaluations += 1
        phase = "source" if self._evaluations == 1 else "output"
        assert len(tokens) == (2 if phase == "source" else 3)
        self.event("evaluate_" + phase)

    def synchronize(self) -> None:
        self._synchronizations += 1
        self.event("synchronize_" + ("source" if self._synchronizations == 1 else "output"))

    def close(self) -> None:
        self.closed = True
        self._unloaded = True
        self.tokens.clear()
        self.records = ()
        self.event("close")


def test_eager_verified_load_exact_dispatch_and_scoped_results(cache: ModelOnlyCache) -> None:
    populate(cache)
    backend = Backend()
    retained = backend.tokens["retained_vector"]
    held: BorrowedConversion[Token] | None = None

    async def exercise() -> None:
        nonlocal held
        async with conversion_session(manifest(), "huggingface", cache, backend) as result:
            held = result
            assert len(result) == 2
            assert result["retained_vector"].weight is retained
            assert result["retained_vector"].scales is None
            assert result[manifest().tensor_map[0].name].weight.label == "packed"
            assert all(reader.closed for reader in backend.readers.values())
            assert not backend.closed
            with pytest.raises(TypeError):
                result["extra"] = result["retained_vector"]  # type: ignore[index]

    asyncio.run(exercise())
    assert backend.events == [
        "load",
        "evaluate_source",
        "synchronize_source",
        "describe:" + manifest().tensor_map[0].name,
        "describe:retained_vector",
        "quantize",
        "evaluate_output",
        "synchronize_output",
        "close",
    ]
    assert backend.closed and held is not None
    with pytest.raises(BlockedEvidence, match="borrow_closed"):
        held["retained_vector"]
    # Honest boundary: Python raw references that escaped the borrow are not revoked.
    assert retained.label == "retained_vector"
    assert_released(cache)


@pytest.mark.parametrize("mismatch", ["converter_revision", "dependency_lock_sha256", "unloaded"])
def test_pre_admission_rejection_performs_zero_work_and_does_not_take_backend(
    cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    backend = Backend()
    if mismatch == "unloaded":
        backend._unloaded = False
    else:
        setattr(backend, mismatch, "different")

    def forbidden(*args: object) -> None:
        raise AssertionError("source work before pin check")

    monkeypatch.setattr(cache, "open_verified_source", forbidden)

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence, match="conversion_backend"):
            async with conversion_session(manifest(), "huggingface", cache, backend):
                pytest.fail("rejected backend admitted")

    asyncio.run(exercise())
    assert backend.events == [] and not backend.closed


@pytest.mark.parametrize("missing", [False, True])
def test_bad_or_unavailable_source_prevents_backend_load(
    cache: ModelOnlyCache, tmp_path: Path, missing: bool
) -> None:
    populate(cache)
    key = hashlib.sha256("|".join(asset_identity(1)).encode()).hexdigest()
    file = tmp_path / "cache" / f"{key}.asset"
    if missing:
        file.unlink()
    else:
        file.write_bytes(b"damaged ordinary notice")
    backend = Backend()

    def unavailable() -> None:
        raise BlockedEvidence("test_transport_unavailable")

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence):
            async with conversion_session(
                manifest(),
                "huggingface",
                cache,
                backend,
                response_factory=unavailable,  # type: ignore[arg-type]
            ):
                pytest.fail("source failure converted")

    asyncio.run(exercise())
    assert backend.events == ["close"] and backend.closed
    assert_released(cache)


@pytest.mark.parametrize("kind", ["missing", "extra", "duplicate", "unknown"])
def test_decoded_name_inventory_is_exact_before_conversion(
    cache: ModelOnlyCache, kind: str
) -> None:
    populate(cache)
    backend = Backend()
    first, second = backend.records
    backend.records = {
        "missing": (first,),
        "extra": (first, second, ("extra", Token("extra"))),
        "duplicate": (first, first),
        "unknown": (first, ("unknown", second[1])),
    }[kind]

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence, match="tensor_inventory_mismatch"):
            async with conversion_session(manifest(), "huggingface", cache, backend):
                pytest.fail("bad inventory yielded")

    asyncio.run(exercise())
    assert backend.events == ["load", "close"]
    assert_released(cache)


@pytest.mark.parametrize(
    "kind",
    ["swapped", "shape_zero", "shape_bool", "shape_empty", "incompatible", "dtype", "unclassified"],
)
def test_all_descriptions_validate_before_first_quantization(
    cache: ModelOnlyCache, kind: str
) -> None:
    populate(cache)
    backend = Backend()
    first, last = manifest().tensor_map
    if kind == "swapped":
        backend.descriptions[first.name], backend.descriptions[last.name] = (
            backend.descriptions[last.name],
            backend.descriptions[first.name],
        )
    else:
        target = first.name if kind == "incompatible" else last.name
        description = backend.descriptions[target]
        if kind.startswith("shape_"):
            shape = {"shape_zero": (0,), "shape_bool": (True,), "shape_empty": ()}[kind]
            description = description.model_copy(update={"shape": shape})
        elif kind == "incompatible":
            description = description.model_copy(update={"shape": (2, 63)})
        else:
            field, value = (
                ("source_dtype", "float16") if kind == "dtype" else ("classification", "unknown")
            )
            description = description.model_copy(
                update={"rule": description.rule.model_copy(update={field: value})}
            )
        backend.descriptions[target] = description

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence):
            async with conversion_session(manifest(), "huggingface", cache, backend):
                pytest.fail("bad description yielded")

    asyncio.run(exercise())
    assert "quantize" not in backend.events and backend.closed
    assert_released(cache)


STAGES = (
    "load",
    "evaluate_source",
    "synchronize_source",
    "describe:retained_vector",
    "quantize",
    "evaluate_output",
    "synchronize_output",
)


@pytest.mark.parametrize("stage", (*STAGES, "close"))
def test_backend_faults_cleanup_and_keep_fixed_diagnostics(
    cache: ModelOnlyCache, stage: str
) -> None:
    populate(cache)
    backend = Backend()
    held: BorrowedConversion[Token] | None = None

    def fail(event: str) -> None:
        if event == stage:
            raise RuntimeError("untrusted backend private diagnostic")

    backend.on_event = fail

    async def exercise() -> None:
        nonlocal held
        with pytest.raises(BlockedEvidence) as caught:
            async with conversion_session(manifest(), "huggingface", cache, backend) as result:
                held = result
                assert stage == "close"
        assert "private" not in str(caught.value)

    asyncio.run(exercise())
    assert backend.closed and backend.events.count("close") == 1
    assert all(reader.closed for reader in backend.readers.values())
    if held is not None:
        with pytest.raises(BlockedEvidence, match="borrow_closed"):
            len(held)
    assert_released(cache)


@pytest.mark.parametrize("stage", STAGES)
def test_observed_cancellation_rejects_returned_stage_result(
    cache: ModelOnlyCache, stage: str
) -> None:
    populate(cache)
    backend = Backend()
    cancelled = False

    def cancel(event: str) -> None:
        nonlocal cancelled
        if event == stage:
            cancelled = True

    backend.on_event = cancel

    async def exercise() -> None:
        async with conversion_session(
            manifest(), "huggingface", cache, backend, cancelled=lambda: cancelled
        ):
            pytest.fail("cancelled result delivered")

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise())
    assert backend.closed and backend.events[-1] == "close"
    assert all(reader.closed for reader in backend.readers.values())
    assert_released(cache)


@pytest.mark.parametrize("field", ["converter_revision", "dependency_lock_sha256"])
def test_pin_drift_during_eager_decode_rejects_result(cache: ModelOnlyCache, field: str) -> None:
    populate(cache)
    backend = Backend()

    def drift(event: str) -> None:
        if event == "load":
            setattr(backend, field, "changed")

    backend.on_event = drift

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence, match="backend_mismatch"):
            async with conversion_session(manifest(), "huggingface", cache, backend):
                pytest.fail("changed pin yielded")

    asyncio.run(exercise())
    assert backend.events == ["load", "close"]
    assert_released(cache)


def test_consumer_cancellation_revokes_mapping_and_closes_backend(cache: ModelOnlyCache) -> None:
    populate(cache)
    backend = Backend()
    held: BorrowedConversion[Token] | None = None

    async def exercise() -> None:
        nonlocal held
        async with conversion_session(manifest(), "huggingface", cache, backend) as result:
            held = result
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise())
    assert held is not None and backend.closed
    with pytest.raises(BlockedEvidence, match="borrow_closed"):
        list(held)
    assert_released(cache)


@pytest.mark.parametrize("stage", ["load", "evaluate_output", "after_dispatch"])
def test_owned_references_release_even_when_cancellation_traceback_is_retained(
    cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    populate(cache)
    references: list[weakref.ReferenceType[Token]] = []
    cancelled = False

    class TrackingBackend(Backend):
        def quantize(
            self, token: Token, *, group_size: int, bits: int, mode: str
        ) -> tuple[Token, Token, Token]:
            values = super().quantize(token, group_size=group_size, bits=bits, mode=mode)
            references.extend(weakref.ref(value) for value in values)
            return values

    backend = TrackingBackend()
    references.extend(weakref.ref(token) for token in backend.tokens.values())

    def observe(event: str) -> None:
        nonlocal cancelled
        if event == stage:
            cancelled = True

    backend.on_event = observe

    def dispatch(
        record: PreparationManifest,
        assets: tuple[Asset, ...],
        tensors: Mapping[str, Token],
        backend: ConversionBackend[Token],
    ) -> dict[str, ConvertedTensor[Token]]:
        result = convert_verified_tensors(record, assets, tensors, backend)
        observe("after_dispatch")
        return result

    monkeypatch.setattr(session_module, "convert_verified_tensors", dispatch)
    retained: list[BaseException] = []

    async def exercise() -> None:
        try:
            async with conversion_session(
                manifest(), "huggingface", cache, backend, cancelled=lambda: cancelled
            ):
                pytest.fail("late result escaped")
        except asyncio.CancelledError as error:
            # Keep the exception and its frames alive, not merely its diagnostic string.
            retained.append(error)

    asyncio.run(exercise())
    assert len(retained) == 1 and retained[0].__traceback__ is not None
    assert backend.closed and backend.events.count("close") == 1
    gc.collect()
    assert references and all(reference() is None for reference in references)
    assert_released(cache)
