"""Cooperative conversion-to-storage bridge, without an installed model serializer.

Only the bridge can commit. Public borrows expire before backend cleanup; this is
not a sandbox against reflection, escaped raw references, or synchronous blocking.
"""

import asyncio
from collections.abc import Callable, Iterable, Iterator, Mapping
from pathlib import Path
from typing import Literal, Protocol

from .cache_reader import VerifiedModelReader
from .contracts import PreparationManifest, metadata_digest
from .conversion import ConvertedTensor, TensorShape
from .conversion_session import PreparationConversionBackend, conversion_session
from .converted_store import ConversionReceipt, ConversionStaging, OutputPlan
from .http_transfer import ModelResponse
from .model_cache import ModelOnlyCache
from .runtime import BlockedEvidence
from .source_cache import VerifiedSourceAssets


class ModelInput(Protocol):
    @property
    def size(self) -> int: ...

    def read_at(self, offset: int, count: int) -> bytes: ...


class OutputWriter(Protocol):
    def write_output(self, path: str, chunks: Iterable[bytes]) -> None: ...


class PreparationSerializer[T](Protocol):
    converter_revision: str
    dependency_lock_sha256: str

    @property
    def fresh(self) -> bool: ...

    def serialize(
        self,
        preparation: PreparationManifest,
        plan: OutputPlan,
        converted: Mapping[str, ConvertedTensor[T]],
        auxiliary: Mapping[str, ModelInput],
        outputs: OutputWriter,
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> None:
        """Consume only these borrows and emit model-only chunks; set fresh=False.

        Iterators and any internal resources belong to the serializer. No inference,
        path access or network is authorized. No concrete serialization format implied.
        """
        ...

    def close(self) -> None:
        """Release owned resources without using expired input/output borrows."""
        ...


class _Guard[T]:
    def __init__(
        self,
        preparation: PreparationManifest,
        mode: Literal["huggingface", "modelscope"],
        cache: ModelOnlyCache,
        converter: PreparationConversionBackend[T],
        serializer: PreparationSerializer[T],
        cancelled: Callable[[], bool],
    ) -> None:
        self.preparation, self.mode, self.cache = preparation, mode, cache
        self.converter, self.serializer = converter, serializer
        self.cancelled = cancelled
        self.failed = self.cancel_seen = False

    def poison(self, error: BaseException) -> None:
        self.failed = True
        if isinstance(error, asyncio.CancelledError):
            self.cancel_seen = True

    def is_cancelled(self) -> bool:
        task = asyncio.current_task()
        if self.cancelled() or (task is not None and task.cancelling()):
            self.cancel_seen = self.failed = True
        return self.cancel_seen

    def check(self) -> None:
        try:
            if self.is_cancelled():
                raise asyncio.CancelledError
            if self.failed:
                raise BlockedEvidence("serialization_failed")
            self.cache.require_preparation(self.preparation, self.mode)
            for backend in (self.converter, self.serializer):
                if (
                    backend.converter_revision != self.preparation.converter_revision
                    or backend.dependency_lock_sha256 != self.preparation.dependency_lock_sha256
                ):
                    raise BlockedEvidence("serialization_backend_mismatch")
        except BaseException as error:
            self.poison(error)
            raise


class _Lease[T]:
    def __init__(self, guard: _Guard[T]) -> None:
        self.guard, self.active = guard, True

    def check(self) -> None:
        if not self.active:
            error = BlockedEvidence("serialization_borrow_closed")
            self.guard.poison(error)
            raise error
        self.guard.check()


class _BorrowedMap[V, T](Mapping[str, V]):
    def __init__(self, values: Mapping[str, V], lease: _Lease[T]) -> None:
        self._values, self._lease = dict(values), lease

    def __getitem__(self, name: str) -> V:
        self._lease.check()
        return self._values[name]

    def __iter__(self) -> Iterator[str]:
        self._lease.check()
        for name in tuple(self._values):
            self._lease.check()
            yield name

    def __len__(self) -> int:
        self._lease.check()
        return len(self._values)


class _Input[T]:
    def __init__(self, reader: VerifiedModelReader, lease: _Lease[T]) -> None:
        self._reader, self._lease = reader, lease

    @property
    def size(self) -> int:
        self._lease.check()
        return self._reader.size

    def read_at(self, offset: int, count: int) -> bytes:
        try:
            self._lease.check()
            result = self._reader.read_at(offset, count)
            self._lease.check()
            return result
        except BaseException as error:
            self._lease.guard.poison(error)
            raise


class _Outputs[T]:
    def __init__(self, store: ConversionStaging, lease: _Lease[T]) -> None:
        self._store, self._lease = store, lease

    def write_output(self, path: str, chunks: Iterable[bytes]) -> None:
        iterator: Iterator[bytes] | None = None
        chunk: bytes | None = None
        try:
            self._lease.check()
            iterator = iter(chunks)
            with self._store.open_output(path) as sink:
                while True:
                    self._lease.check()
                    try:
                        chunk = next(iterator)
                    except StopIteration:
                        break
                    self._lease.check()
                    sink.write(chunk)
                self._lease.check()
        except BaseException as error:
            self._lease.guard.poison(error)
            if isinstance(error, BlockedEvidence | asyncio.CancelledError):
                raise
            raise BlockedEvidence("serialization_output_failed") from None
        finally:
            chunk = iterator = None
            del chunks


class _OwnedConverter[T]:
    """Close-once adapter shared with conversion_session's existing ownership scope."""

    def __init__(self, backend: PreparationConversionBackend[T]) -> None:
        self.backend, self.closed = backend, False

    @property
    def converter_revision(self) -> str:
        return self.backend.converter_revision

    @converter_revision.setter
    def converter_revision(self, value: str) -> None:
        self.backend.converter_revision = value

    @property
    def dependency_lock_sha256(self) -> str:
        return self.backend.dependency_lock_sha256

    @dependency_lock_sha256.setter
    def dependency_lock_sha256(self, value: str) -> None:
        self.backend.dependency_lock_sha256 = value

    @property
    def unloaded(self) -> bool:
        return self.backend.unloaded

    def load_sources(
        self,
        manifest: PreparationManifest,
        assets: Mapping[str, VerifiedModelReader],
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> tuple[tuple[str, T], ...]:
        return self.backend.load_sources(
            manifest, assets, local_files_only=local_files_only, trust_remote_code=trust_remote_code
        )

    def describe(self, name: str, tensor: T) -> TensorShape:
        try:
            return self.backend.describe(name, tensor)
        finally:
            del tensor

    def quantize(self, tensor: T, *, group_size: int, bits: int, mode: str) -> tuple[T, T, T]:
        try:
            return self.backend.quantize(tensor, group_size=group_size, bits=bits, mode=mode)
        finally:
            del tensor

    def evaluate(self, tensors: tuple[T, ...]) -> None:
        try:
            self.backend.evaluate(tensors)
        finally:
            del tensors

    def synchronize(self) -> None:
        self.backend.synchronize()

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.backend.close()


class _Owners[T]:
    def __init__(
        self, converter: PreparationConversionBackend[T], serializer: PreparationSerializer[T]
    ) -> None:
        self.converter, self.serializer = _OwnedConverter(converter), serializer
        self.serializer_closed = False

    def close_serializer(self) -> None:
        if not self.serializer_closed:
            self.serializer_closed = True
            if id(self.serializer) == id(self.converter.backend):
                if self.converter.closed:
                    return
                # Two roles may share one object; close it once in either unwind order.
                self.converter.closed = True
            try:
                self.serializer.close()
            except BaseException:
                raise BlockedEvidence("serialization_cleanup_failed") from None

    def close(self) -> None:
        failed = False
        for close in (self.close_serializer, self.converter.close):
            try:
                close()
            except BaseException:
                failed = True
        if failed:
            raise BlockedEvidence("serialization_cleanup_failed")


def _no_download() -> ModelResponse:
    raise BlockedEvidence("serialization_requires_local_sources")


def _probe_local[T](guard: _Guard[T]) -> None:
    owner = VerifiedSourceAssets(guard.preparation, guard.mode, guard.cache, guard.is_cancelled)
    try:
        owner.open_assets()
        guard.check()
    finally:
        owner.close()


def _serialize[T](
    guard: _Guard[T],
    plan: OutputPlan,
    converted: Mapping[str, ConvertedTensor[T]],
    store: ConversionStaging,
) -> None:
    lease = _Lease(guard)
    source = VerifiedSourceAssets(guard.preparation, guard.mode, guard.cache, guard.is_cancelled)
    tensors: _BorrowedMap[ConvertedTensor[T], T] | None = None
    auxiliary: _BorrowedMap[ModelInput, T] | None = None
    result: object = None
    try:
        guard.check()
        readers = source.open_assets()
        tensors = _BorrowedMap(converted, lease)
        auxiliary = _BorrowedMap(
            {
                asset.path: _Input(readers[asset.path], lease)
                for asset in guard.preparation.source_assets
                if asset.kind != "weights"
            },
            lease,
        )
        if guard.serializer.fresh is not True:
            raise BlockedEvidence("serialization_backend_not_fresh")
        # Reject a runtime backend that violates the declared None-return contract.
        result = guard.serializer.serialize(  # type: ignore[func-returns-value]
            guard.preparation,
            plan,
            tensors,
            auxiliary,
            _Outputs(store, lease),
            local_files_only=True,
            trust_remote_code=False,
        )
        guard.check()
        if result is not None or guard.serializer.fresh is not False:
            raise BlockedEvidence("serialization_backend_state")
        for reader in readers.values():
            reader.validate()
        guard.check()
    finally:
        result = None
        lease.active = False
        if tensors is not None:
            tensors._values.clear()
        if auxiliary is not None:
            auxiliary._values.clear()
        source.close()


async def prepare_converted_artifacts[T](
    preparation: PreparationManifest,
    mode: Literal["huggingface", "modelscope"],
    cache: ModelOnlyCache,
    converter: PreparationConversionBackend[T],
    serializer: PreparationSerializer[T],
    plan: OutputPlan,
    output_root: Path,
    repository_root: Path,
    *,
    cancelled: Callable[[], bool] = lambda: False,
) -> ConversionReceipt:
    """Admit both backends, serialize existing verified local inputs, then commit.

    Admission failure leaves both backends with the caller. After admission both are
    closed once on all exits, including storage or inner conversion-admission failure.
    A post-rename error preserves the storage receipt and never returns success.
    """
    try:
        preparation = PreparationManifest.model_validate(preparation.model_dump())
        plan = OutputPlan.model_validate(plan.model_dump())
        if (
            plan.preparation_sha256 != metadata_digest(preparation)
            or plan.converter_revision != preparation.converter_revision
            or plan.dependency_lock_sha256 != preparation.dependency_lock_sha256
        ):
            raise BlockedEvidence("serialization_plan_binding")
        guard = _Guard(preparation, mode, cache, converter, serializer, cancelled)
        guard.check()
        if converter.unloaded is not True or serializer.fresh is not True:
            raise BlockedEvidence("serialization_backend_not_fresh")
    except BaseException as error:
        if isinstance(error, BlockedEvidence | asyncio.CancelledError):
            raise
        raise BlockedEvidence("serialization_admission_failed") from None

    owners = _Owners(converter, serializer)
    try:
        with ConversionStaging(
            output_root, repository_root, preparation, plan, cancelled=guard.is_cancelled
        ) as store:
            try:
                _probe_local(guard)
                async with conversion_session(
                    preparation,
                    mode,
                    cache,
                    owners.converter,
                    response_factory=_no_download,
                    cancelled=guard.is_cancelled,
                ) as converted:
                    try:
                        _serialize(guard, plan, converted, store)
                    finally:
                        owners.close_serializer()
            finally:
                owners.close()
            guard.check()
            receipt = store.commit()
        guard.check()
        return receipt
    except BaseException as error:
        if isinstance(error, BlockedEvidence | asyncio.CancelledError):
            raise
        raise BlockedEvidence("serialization_failed") from None
    finally:
        owners.close()
