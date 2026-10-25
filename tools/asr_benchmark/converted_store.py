"""Model-only storage transactions; receipts record bytes, never inference approval.

An injected, separately reviewed serializer may use the bounded sink. This module does
not implement or validate any model file format. A receipt is the complete-set commit;
individual content files published earlier can survive a failed transaction as orphans.
"""

import asyncio
import fcntl
import hashlib
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import Field, field_validator, model_validator

from .cache_reader import MissingModelAsset, VerifiedModelReader
from .contracts import Asset, Closed, Digest, PreparationManifest, Revision, metadata_digest
from .model_cache import Fingerprint, ModelCacheEntry, _fingerprint, _private_file, _root_fd
from .runtime import BlockedEvidence

CHUNK_BYTES = 1024**2
RECEIPT_BYTES = 256 * 1024
Kind = Literal["weights", "tokenizer", "config", "notice"]


class OutputSpec(Closed):
    path: Annotated[str, Field(min_length=1, max_length=200)]
    kind: Kind
    max_bytes: Annotated[int, Field(gt=0, le=64 * 1024**3)]

    @field_validator("path")
    @classmethod
    def model_path(cls, value: str) -> str:
        return Asset.safe_asset_path(value)


class OutputPlan(Closed):
    preparation_sha256: Digest
    converter_revision: Revision
    dependency_lock_sha256: Digest
    outputs: Annotated[tuple[OutputSpec, ...], Field(min_length=1, max_length=256)]
    max_total_bytes: Annotated[int, Field(gt=0, le=128 * 1024**3)]

    @model_validator(mode="after")
    def complete(self) -> Self:
        if len({item.path for item in self.outputs}) != len(self.outputs):
            raise ValueError("output_inventory")
        if {item.kind for item in self.outputs} != {"weights", "tokenizer", "config", "notice"}:
            raise ValueError("output_kinds")
        if any(item.max_bytes > self.max_total_bytes for item in self.outputs):
            raise ValueError("output_bounds")
        return self


class ConversionReceipt(Closed):
    schema_version: Literal[1] = 1
    status: Literal["unapproved"] = "unapproved"
    preparation_sha256: Digest
    source_revision: Revision
    converter_revision: Revision
    dependency_lock_sha256: Digest
    output_plan_sha256: Digest
    outputs: Annotated[tuple[Asset, ...], Field(min_length=1, max_length=256)]


def _check_cancelled(cancelled: Callable[[], bool]) -> None:
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    if cancelled() or (task is not None and task.cancelling()):
        raise asyncio.CancelledError


def _named_stamp(directory: int, name: str, fd: int) -> Fingerprint:
    stamp = _fingerprint(_private_file(fd))
    named = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if _fingerprint(named) != stamp:
        raise BlockedEvidence("conversion_file_changed")
    return stamp


def _write_all(fd: int, chunk: bytes) -> None:
    with memoryview(chunk) as view:
        written = 0
        while written < len(view):
            count = os.write(fd, view[written:])
            if count <= 0:
                raise BlockedEvidence("conversion_short_write")
            written += count


class _Store:
    def __init__(
        self,
        root: Path,
        repository_root: Path,
        preparation: PreparationManifest,
        plan: OutputPlan,
        cancelled: Callable[[], bool],
        *,
        create: bool,
    ) -> None:
        self.directory = self.lock = -1
        self.closed = False
        self.cancelled = cancelled
        try:
            self.preparation = PreparationManifest.model_validate(preparation.model_dump())
            self.plan = OutputPlan.model_validate(plan.model_dump())
            if (
                self.plan.preparation_sha256 != metadata_digest(self.preparation)
                or self.plan.converter_revision != self.preparation.converter_revision
                or self.plan.dependency_lock_sha256 != self.preparation.dependency_lock_sha256
            ):
                raise BlockedEvidence("conversion_plan_binding")
            _check_cancelled(cancelled)
            self.directory = _root_fd(root, repository_root, create=create)
            self.lock_name = f"conversion-{self.plan.preparation_sha256}.lock"
            self.receipt_name = (
                f"conversion-{self.plan.preparation_sha256}-{metadata_digest(self.plan)}.receipt"
            )
            self.lock = os.open(
                self.lock_name,
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=self.directory,
            )
            self.lock_stamp = _named_stamp(self.directory, self.lock_name, self.lock)
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.check()
        except BaseException as error:
            self.close()
            if isinstance(error, BlockedEvidence | asyncio.CancelledError):
                raise
            raise BlockedEvidence("conversion_store_unavailable") from None

    def check(self) -> None:
        if self.closed:
            raise BlockedEvidence("conversion_store_closed")
        _check_cancelled(self.cancelled)
        if _named_stamp(self.directory, self.lock_name, self.lock) != self.lock_stamp:
            raise BlockedEvidence("conversion_lock_changed")

    def entry(self, asset: Asset) -> ModelCacheEntry:
        return ModelCacheEntry(
            self.directory,
            (self.plan.preparation_sha256, self.preparation.source_revision, asset.sha256),
            asset,
            "huggingface",  # Canonical final namespace, not a source-mirror selection.
        )

    def bind_receipt(self, receipt: ConversionReceipt) -> None:
        expected = self.plan
        if (
            receipt.preparation_sha256 != expected.preparation_sha256
            or receipt.source_revision != self.preparation.source_revision
            or receipt.converter_revision != expected.converter_revision
            or receipt.dependency_lock_sha256 != expected.dependency_lock_sha256
            or receipt.output_plan_sha256 != metadata_digest(expected)
            or len(receipt.outputs) != len(expected.outputs)
        ):
            raise BlockedEvidence("conversion_receipt_binding")
        total = 0
        for asset, spec in zip(receipt.outputs, expected.outputs, strict=True):
            if (asset.path, asset.kind) != (spec.path, spec.kind) or asset.size > spec.max_bytes:
                raise BlockedEvidence("conversion_receipt_inventory")
            total += asset.size
        if total > expected.max_total_bytes:
            raise BlockedEvidence("conversion_receipt_bounds")

    def receipt(self) -> ConversionReceipt | None:
        self.check()
        fd = -1
        try:
            try:
                fd = os.open(
                    self.receipt_name,
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=self.directory,
                )
            except FileNotFoundError:
                return None
            before = _named_stamp(self.directory, self.receipt_name, fd)
            if not 0 < before[2] <= RECEIPT_BYTES:
                raise BlockedEvidence("conversion_receipt_bounds")
            payload = os.read(fd, RECEIPT_BYTES + 1)
            if len(payload) != before[2]:
                raise BlockedEvidence("conversion_receipt_changed")
            receipt = ConversionReceipt.model_validate_json(payload)
            self.bind_receipt(receipt)
            if _named_stamp(self.directory, self.receipt_name, fd) != before:
                raise BlockedEvidence("conversion_receipt_changed")
            self.check()
            return receipt
        finally:
            if fd != -1:
                os.close(fd)

    def verify_assets(self, receipt: ConversionReceipt) -> None:
        readers: list[VerifiedModelReader] = []
        try:
            unique: dict[str, Asset] = {}
            for asset in receipt.outputs:
                if asset.sha256 in unique and unique[asset.sha256].size != asset.size:
                    raise BlockedEvidence("conversion_receipt_inventory")
                unique[asset.sha256] = asset
            for asset in sorted(unique.values(), key=lambda value: value.sha256):
                self.check()
                readers.append(
                    VerifiedModelReader.from_entry(
                        self.entry(asset), self.cancelled, owns_entry=True
                    )
                )
            for reader in readers:
                reader.validate()
            self.check()
        finally:
            failed = False
            for reader in readers:
                try:
                    reader.close()
                except BaseException:
                    failed = True
            if failed:
                raise BlockedEvidence("conversion_reader_cleanup")

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        failed = False
        for fd in (self.lock, self.directory):
            if fd != -1:
                try:
                    os.close(fd)
                except BaseException:
                    failed = True
        self.lock = self.directory = -1
        if failed:
            raise BlockedEvidence("conversion_store_cleanup")


def read_conversion_receipt(
    root: Path,
    repository_root: Path,
    preparation: PreparationManifest,
    plan: OutputPlan,
    *,
    cancelled: Callable[[], bool] = lambda: False,
) -> ConversionReceipt:
    """Read and rehash the complete set; this returns no inference authority."""
    store = _Store(root, repository_root, preparation, plan, cancelled, create=False)
    try:
        receipt = store.receipt()
        if receipt is None:
            raise BlockedEvidence("conversion_receipt_missing")
        store.verify_assets(receipt)
        return receipt
    except BaseException as error:
        if isinstance(error, BlockedEvidence | asyncio.CancelledError):
            raise
        raise BlockedEvidence("conversion_receipt_invalid") from None
    finally:
        store.close()


@dataclass
class _Output:
    spec: OutputSpec
    name: str
    fd: int
    stamp: Fingerprint
    asset: Asset | None = None


class ModelOutputSink:
    """Borrowed sequential model-byte writer; no seek, path, fd or audio interface."""

    def __init__(self, owner: "ConversionStaging", output: _Output) -> None:
        self._owner, self._output = owner, output
        self._active = True

    def write(self, chunk: bytes) -> None:
        if not self._active:
            raise BlockedEvidence("conversion_sink_closed")
        self._owner._append(self._output, chunk)


class ConversionStaging:
    """One cooperative serializer transaction; only commit() publishes a receipt.

    Published immutable assets/receipts are never rolled back. Close removes only the
    names created inside this transaction's private stage; crash orphans are not GC'd.
    """

    def __init__(
        self,
        root: Path,
        repository_root: Path,
        preparation: PreparationManifest,
        plan: OutputPlan,
        *,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> None:
        self._store = _Store(root, repository_root, preparation, plan, cancelled, create=True)
        self._stage = -1
        self._stage_name = f"conversion-{uuid4().hex}.stage"
        self._stage_identity: tuple[int, int] | None = None
        self._owned: dict[str, tuple[int, int]] = {}
        self._outputs: dict[str, _Output] = {}
        self._active: _Output | None = None
        self._total = 0
        self._failed = self._committed = self.closed = False
        try:
            os.mkdir(self._stage_name, mode=0o700, dir_fd=self._store.directory)
            created = os.stat(self._stage_name, dir_fd=self._store.directory, follow_symlinks=False)
            self._stage_identity = (created.st_dev, created.st_ino)
            self._stage = os.open(
                self._stage_name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=self._store.directory,
            )
            stat = os.fstat(self._stage)
            if (stat.st_dev, stat.st_ino) != self._stage_identity:
                raise BlockedEvidence("conversion_stage_changed")
            self._check()
        except BaseException as error:
            self.close()
            if isinstance(error, asyncio.CancelledError):
                raise
            raise BlockedEvidence("conversion_stage_unavailable") from None

    def _check(self) -> None:
        self._store.check()
        if self.closed or self._failed or self._committed:
            raise BlockedEvidence("conversion_transaction_closed")
        named = os.stat(self._stage_name, dir_fd=self._store.directory, follow_symlinks=False)
        if (named.st_dev, named.st_ino) != self._stage_identity or named.st_mode & 0o077:
            raise BlockedEvidence("conversion_stage_changed")

    @contextmanager
    def _operation(self) -> Iterator[None]:
        try:
            self._check()
            yield
            self._check()
        except BaseException as error:
            self._failed = True
            if isinstance(error, BlockedEvidence | asyncio.CancelledError):
                raise
            raise BlockedEvidence("conversion_storage_failed") from None

    def _create(self, name: str) -> int:
        fd = os.open(
            name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self._stage
        )
        try:
            value = os.fstat(fd)
            self._owned[name] = (value.st_dev, value.st_ino)
            _named_stamp(self._stage, name, fd)
            return fd
        except BaseException:
            os.close(fd)
            raise

    @contextmanager
    def open_output(self, path: str) -> Iterator[ModelOutputSink]:
        with self._operation():
            specs = {item.path: item for item in self._store.plan.outputs}
            if type(path) is not str or path not in specs or path in self._outputs:
                raise BlockedEvidence("conversion_output_denied")
            if self._active is not None:
                raise BlockedEvidence("conversion_output_busy")
            name = f"{len(self._outputs)}.output"
            fd = self._create(name)
            try:
                stamp = _named_stamp(self._stage, name, fd)
            except BaseException:
                os.close(fd)
                raise
            output = _Output(specs[path], name, fd, stamp)
            self._outputs[path] = self._active = output
            sink = ModelOutputSink(self, output)
            try:
                yield sink
                self._finish(output)
            finally:
                sink._active = False
                self._active = None

    def _append(self, output: _Output, chunk: bytes) -> None:
        with self._operation():
            if output is not self._active or output.asset is not None:
                raise BlockedEvidence("conversion_sink_closed")
            if (
                type(chunk) is not bytes
                or not 0 < len(chunk) <= CHUNK_BYTES
                or output.stamp[2] + len(chunk) > output.spec.max_bytes
                or self._total + len(chunk) > self._store.plan.max_total_bytes
            ):
                raise BlockedEvidence("conversion_output_bounds")
            if _named_stamp(self._stage, output.name, output.fd) != output.stamp:
                raise BlockedEvidence("conversion_output_changed")
            _write_all(output.fd, chunk)
            current = _named_stamp(self._stage, output.name, output.fd)
            if current[2] != output.stamp[2] + len(chunk):
                raise BlockedEvidence("conversion_output_changed")
            output.stamp = current
            self._total += len(chunk)

    def _finish(self, output: _Output) -> None:
        self._check()
        before = _named_stamp(self._stage, output.name, output.fd)
        if before != output.stamp or before[2] == 0:
            raise BlockedEvidence("conversion_output_changed")
        os.fsync(output.fd)
        digest = hashlib.sha256()
        offset = 0
        while offset < before[2]:
            self._check()
            chunk = os.pread(output.fd, min(CHUNK_BYTES, before[2] - offset), offset)
            if not chunk:
                raise BlockedEvidence("conversion_output_changed")
            digest.update(chunk)
            offset += len(chunk)
        if (
            os.pread(output.fd, 1, offset)
            or _named_stamp(self._stage, output.name, output.fd) != before
        ):
            raise BlockedEvidence("conversion_output_changed")
        output.asset = Asset(
            path=output.spec.path, kind=output.spec.kind, size=offset, sha256=digest.hexdigest()
        )

    def _publish(self, output: _Output) -> None:
        assert output.asset is not None
        if _named_stamp(self._stage, output.name, output.fd) != output.stamp:
            raise BlockedEvidence("conversion_output_changed")
        # Use the normal final-asset lock only after the actual digest is known.
        entry = self._store.entry(output.asset)
        try:
            try:
                reader = VerifiedModelReader.from_entry(
                    entry, self._store.cancelled, owns_entry=False
                )
            except MissingModelAsset:
                self._check()
                os.rename(
                    output.name,
                    entry._name("asset"),
                    src_dir_fd=self._stage,
                    dst_dir_fd=self._store.directory,
                )
                current = _named_stamp(self._store.directory, entry._name("asset"), output.fd)
                if current[:4] != output.stamp[:4]:
                    raise BlockedEvidence("conversion_promotion_changed") from None
                os.fsync(output.fd)
                os.fsync(self._store.directory)
            else:
                reader.close()
        finally:
            entry.close()

    def commit(self) -> ConversionReceipt:
        # After rename, a late error preserves the receipt and reports uncertain outcome.
        with self._operation():
            if self._active or set(self._outputs) != {a.path for a in self._store.plan.outputs}:
                raise BlockedEvidence("conversion_output_incomplete")
            assets = tuple(self._outputs[spec.path].asset for spec in self._store.plan.outputs)
            if any(asset is None for asset in assets):
                raise BlockedEvidence("conversion_output_incomplete")
            receipt = ConversionReceipt(
                preparation_sha256=self._store.plan.preparation_sha256,
                source_revision=self._store.preparation.source_revision,
                converter_revision=self._store.plan.converter_revision,
                dependency_lock_sha256=self._store.plan.dependency_lock_sha256,
                output_plan_sha256=metadata_digest(self._store.plan),
                outputs=tuple(asset for asset in assets if asset is not None),
            )
            self._store.bind_receipt(receipt)
            existing = self._store.receipt()
            if existing is not None and existing != receipt:
                raise BlockedEvidence("conversion_receipt_conflict")
            if existing is not None:
                # A previously committed set must still verify; a retry is not repair
                # authority for its missing or damaged contents.
                self._store.verify_assets(existing)
            for spec in self._store.plan.outputs:
                self._check()
                self._publish(self._outputs[spec.path])
            self._store.verify_assets(receipt)
            if existing is None:
                payload = receipt.model_dump_json().encode("utf-8")
                if len(payload) > RECEIPT_BYTES:
                    raise BlockedEvidence("conversion_receipt_bounds")
                fd = self._create("receipt.new")
                try:
                    _write_all(fd, payload)
                    os.fsync(fd)
                    stamp = _named_stamp(self._stage, "receipt.new", fd)
                    if (
                        stamp[2] != len(payload)
                        or os.pread(fd, RECEIPT_BYTES + 1, 0) != payload
                        or _named_stamp(self._stage, "receipt.new", fd) != stamp
                    ):
                        raise BlockedEvidence("conversion_receipt_changed")
                    self._check()
                    os.rename(
                        "receipt.new",
                        self._store.receipt_name,
                        src_dir_fd=self._stage,
                        dst_dir_fd=self._store.directory,
                    )
                    if (
                        _named_stamp(self._store.directory, self._store.receipt_name, fd)[:4]
                        != (stamp[:4])
                    ):
                        raise BlockedEvidence("conversion_receipt_changed")
                    os.fsync(self._store.directory)
                finally:
                    os.close(fd)
            else:
                # Retry may follow an earlier rename whose fsync/result was interrupted.
                os.fsync(self._store.directory)
            self._check()
        self._committed = True
        return receipt

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        failed = False
        for output in self._outputs.values():
            if output.fd != -1:
                fd, output.fd = output.fd, -1
                try:
                    os.close(fd)
                except BaseException:
                    failed = True
        if self._stage != -1:
            for name, identity in self._owned.items():
                try:
                    named = os.stat(name, dir_fd=self._stage, follow_symlinks=False)
                    if (named.st_dev, named.st_ino) != identity:
                        raise BlockedEvidence("conversion_cleanup_substitution")
                    os.unlink(name, dir_fd=self._stage)
                except FileNotFoundError:
                    pass  # Published names have moved out of this stage.
                except BaseException:
                    failed = True
        if self._stage_identity is not None:
            try:
                named = os.stat(
                    self._stage_name, dir_fd=self._store.directory, follow_symlinks=False
                )
                if (named.st_dev, named.st_ino) != self._stage_identity:
                    raise BlockedEvidence("conversion_cleanup_substitution")
                os.rmdir(self._stage_name, dir_fd=self._store.directory)
            except BaseException:
                failed = True
        if self._stage != -1:
            try:
                os.close(self._stage)
            except BaseException:
                failed = True
            self._stage = -1
        try:
            self._store.close()
        except BaseException:
            failed = True
        if failed:
            raise BlockedEvidence("conversion_stage_cleanup")
