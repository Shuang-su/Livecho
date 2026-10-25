"""Preparation-only conversion orchestration, with no installed model backend.

Backend methods are synchronous and cooperative. Checks reject observed cancellation
or pin drift between stages; they cannot preempt computation or erase escaped tensors.
"""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping
from contextlib import asynccontextmanager
from functools import partial
from types import MappingProxyType
from typing import Literal, Protocol

from pydantic import ValidationError

from .cache_reader import VerifiedModelReader
from .contracts import PreparationManifest
from .conversion import ConversionBackend, ConvertedTensor, TensorShape, convert_verified_tensors
from .http_transfer import HTTPSResponse, ModelResponse
from .model_cache import ModelOnlyCache
from .preparation import TransferProgress
from .preparation_run import prepare_sources
from .runtime import BlockedEvidence


class PreparationConversionBackend[T](ConversionBackend[T], Protocol):
    converter_revision: str
    dependency_lock_sha256: str

    @property
    def unloaded(self) -> bool: ...

    def load_sources(
        self,
        manifest: PreparationManifest,
        assets: Mapping[str, VerifiedModelReader],
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> tuple[tuple[str, T], ...]:
        """Eagerly consume borrowed files; own all tensors, report unloaded=False.

        Preserve tensor names as records, including duplicates for rejection. Never
        individually close/retain file readers. No network, inference or output writer.
        """
        ...

    def close(self) -> None:
        """Cooperatively release all owned source/output tensors, also after failure."""
        ...


class BorrowedConversion[T](Mapping[str, ConvertedTensor[T]]):
    """Checked mapping valid in its session only; returned raw references cannot revoke."""

    def __init__(self, values: dict[str, ConvertedTensor[T]]) -> None:
        self._values = values
        self._closed = False

    def _check(self) -> None:
        if self._closed:
            raise BlockedEvidence("conversion_borrow_closed")

    def __getitem__(self, name: str) -> ConvertedTensor[T]:
        self._check()
        return self._values[name]

    def __iter__(self) -> Iterator[str]:
        self._check()
        for name in tuple(self._values):
            self._check()
            yield name

    def __len__(self) -> int:
        self._check()
        return len(self._values)

    def close(self) -> None:
        self._closed = True
        self._values.clear()


class _BoundBackend[T]:
    def __init__(
        self,
        manifest: PreparationManifest,
        backend: PreparationConversionBackend[T],
        cancelled: Callable[[], bool],
    ) -> None:
        self.manifest, self.backend, self.cancelled = manifest, backend, cancelled
        self.loaded = False

    def check(self) -> None:
        task = asyncio.current_task()
        if self.cancelled() or (task is not None and task.cancelling() > 0):
            raise asyncio.CancelledError
        if (
            self.backend.converter_revision != self.manifest.converter_revision
            or self.backend.dependency_lock_sha256 != self.manifest.dependency_lock_sha256
        ):
            raise BlockedEvidence("conversion_backend_mismatch")
        if self.loaded and self.backend.unloaded is not False:
            raise BlockedEvidence("conversion_backend_not_loaded")

    def call[R](self, operation: Callable[[], R]) -> R:
        result: R | None = None
        try:
            self.check()
            try:
                result = operation()
            except asyncio.CancelledError:
                raise
            except BaseException:
                raise BlockedEvidence("conversion_backend_failed") from None
            self.check()
            return result
        finally:
            result = None
            del operation

    def describe(self, name: str, tensor: T) -> TensorShape:
        try:
            return self.call(partial(self.backend.describe, name, tensor))
        finally:
            del tensor

    def quantize(self, tensor: T, *, group_size: int, bits: int, mode: str) -> tuple[T, T, T]:
        try:
            return self.call(
                partial(self.backend.quantize, tensor, group_size=group_size, bits=bits, mode=mode)
            )
        finally:
            del tensor

    def evaluate(self, tensors: tuple[T, ...]) -> None:
        try:
            self.call(partial(self.backend.evaluate, tensors))
        finally:
            del tensors

    def synchronize(self) -> None:
        self.call(self.backend.synchronize)


@asynccontextmanager
async def conversion_session[T](
    manifest: PreparationManifest,
    mode: Literal["huggingface", "modelscope"],
    cache: ModelOnlyCache,
    backend: PreparationConversionBackend[T],
    *,
    response_factory: Callable[[], ModelResponse] = HTTPSResponse,
    clock: Callable[[], int] = time.monotonic_ns,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    progress: Callable[[TransferProgress], None] | None = None,
    cancelled: Callable[[], bool] = lambda: False,
) -> AsyncIterator[BorrowedConversion[T]]:
    """Own an admitted backend and borrow the caller's cache; never approve inference.

    Before successful pin/fresh-state admission the caller still owns backend cleanup.
    After admission all paths close it. Returned tensor references remain cooperative
    borrows, not zeroized/forcibly revocable objects or a synchronous deadline guarantee.
    """
    try:
        manifest = PreparationManifest.model_validate(manifest.model_dump())
        cache.require_preparation(manifest, mode)
        bound = _BoundBackend(manifest, backend, cancelled)
        bound.check()
        if backend.unloaded is not True:
            raise BlockedEvidence("conversion_backend_not_fresh")
    except (asyncio.CancelledError, BlockedEvidence):
        raise
    except (AttributeError, ValidationError):
        raise BlockedEvidence("preparation_not_allowlisted") from None
    except BaseException:
        raise BlockedEvidence("conversion_admission_failed") from None

    borrowed: BorrowedConversion[T] | None = None
    converted: dict[str, ConvertedTensor[T]] = {}
    sources: dict[str, T] = {}
    records: tuple[tuple[str, T], ...] = ()
    record: tuple[str, T] | None = None
    tensor: T | None = None
    try:
        async with prepare_sources(
            manifest,
            mode,
            cache,
            response_factory=response_factory,
            clock=clock,
            sleep=sleep,
            progress=progress,
            cancelled=cancelled,
        ) as readers:
            bound.check()
            if backend.unloaded is not True:
                raise BlockedEvidence("conversion_backend_not_fresh")
            records = bound.call(
                partial(
                    backend.load_sources,
                    manifest,
                    readers,
                    local_files_only=True,
                    trust_remote_code=False,
                )
            )
            bound.loaded = True
            bound.check()
            expected = {rule.name for rule in manifest.tensor_map}
            if type(records) is not tuple or len(records) != len(expected):
                raise BlockedEvidence("tensor_inventory_mismatch")
            for record in records:
                if type(record) is not tuple or len(record) != 2:
                    raise BlockedEvidence("tensor_inventory_mismatch")
                name, tensor = record
                if type(name) is not str or name not in expected or name in sources:
                    raise BlockedEvidence("tensor_inventory_mismatch")
                sources[name] = tensor
            bound.evaluate(tuple(sources.values()))
            bound.synchronize()
            for reader in readers.values():
                reader.validate()
            bound.check()
        # No reader survives eager decoding. Actual-file proof came from the context,
        # never from a caller-supplied verified-source tuple.
        bound.check()
        converted = convert_verified_tensors(
            manifest, manifest.source_assets, MappingProxyType(sources), bound
        )
        bound.check()
        borrowed = BorrowedConversion(converted)
        yield borrowed
    except (asyncio.CancelledError, BlockedEvidence):
        raise
    except BaseException:
        raise BlockedEvidence("conversion_session_failed") from None
    finally:
        if borrowed is not None:
            borrowed.close()
        converted.clear()
        sources.clear()
        records = ()
        record = None
        tensor = None
        try:
            backend.close()
        except BaseException:
            raise BlockedEvidence("conversion_cleanup_failed") from None
