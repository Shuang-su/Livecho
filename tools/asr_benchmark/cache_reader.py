"""Final-manifest-bound model readers; no paths, descriptors or network for a loader.

This is a local read boundary, not inference authority. The CLI registry is empty.
Converted assets must already exist under their preparation/canonical-source/digest
keys. No preparation asset is substituted for a missing converted asset.
"""

import hashlib
import os
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path
from types import MappingProxyType, TracebackType
from typing import Literal, Self

from .contracts import Asset, InferenceManifest, PreparationManifest
from .conversion import bind_inference
from .model_cache import (
    Fingerprint,
    Identity,
    ModelCacheEntry,
    _fingerprint,
    _private_file,
    _root_fd,
)
from .runtime import BlockedEvidence

CHUNK_BYTES = 1024**2


class MissingModelAsset(BlockedEvidence):
    """Only a locked final-file open returned ENOENT; other failures are not missing."""


class VerifiedModelReader:
    """Bounded read-at access while holding the cooperating cache's asset lock.

    Path aliases share this borrowed capability and lifetime. The cache/load owner
    closes it; a backend must not individually close a reader or retain it after load.
    """

    def __init__(
        self,
        directory: int,
        identity: Identity,
        asset: Asset,
        cancelled: Callable[[], bool],
        *,
        mode: Literal["huggingface", "modelscope"] = "huggingface",
    ) -> None:
        self._initialize(ModelCacheEntry(directory, identity, asset, mode), cancelled, True)

    @classmethod
    def from_entry(
        cls, entry: ModelCacheEntry, cancelled: Callable[[], bool], *, owns_entry: bool
    ) -> Self:
        """Use an already-held lock; a borrowed reader closes only its final-file fd.

        With owns_entry=False the caller must hold the entry until this reader closes.
        Ownership is transferred otherwise, including constructor failure cleanup.
        """
        value = cls.__new__(cls)
        value._initialize(entry, cancelled, owns_entry)
        return value

    def _initialize(
        self, entry: ModelCacheEntry, cancelled: Callable[[], bool], owns_entry: bool
    ) -> None:
        self._entry = entry
        self._owns_entry = owns_entry
        self._fd = -1
        self._size = entry.asset.size
        self._cancelled = cancelled
        self._stamp: Fingerprint | None = None
        self.closed = False
        try:
            entry._require(entry.identity)
            self._check_cancelled()
            try:
                self._fd = os.open(
                    self._entry._name("asset"),
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=self._entry._directory,
                )
            except FileNotFoundError:
                raise MissingModelAsset("cache_final_missing") from None
            before = _fingerprint(_private_file(self._fd))
            if before[2] != entry.asset.size:
                raise BlockedEvidence("cache_final_length")
            digest = hashlib.sha256()
            offset = 0
            while offset < entry.asset.size:
                self._check_cancelled()
                data = os.pread(self._fd, min(CHUNK_BYTES, entry.asset.size - offset), offset)
                if not data:
                    raise BlockedEvidence("cache_final_length")
                digest.update(data)
                offset += len(data)
            if os.pread(self._fd, 1, entry.asset.size) or digest.hexdigest() != entry.asset.sha256:
                raise BlockedEvidence("cache_final_integrity")
            self._stamp = before
            self.validate()
        except BaseException as error:
            try:
                self.close()
            except BaseException:
                raise BlockedEvidence("cache_reader_close_failed") from None
            if isinstance(error, MissingModelAsset):
                raise
            raise BlockedEvidence("cache_final_invalid") from None

    @property
    def size(self) -> int:
        return self._size

    def _check_cancelled(self) -> None:
        if self.closed or self._cancelled():
            raise BlockedEvidence("cache_reader_unavailable")

    def validate(self) -> None:
        try:
            self._check_cancelled()
            current = _fingerprint(_private_file(self._fd))
            named = os.stat(
                self._entry._name("asset"), dir_fd=self._entry._directory, follow_symlinks=False
            )
            if current != self._stamp or _fingerprint(named) != current:
                raise BlockedEvidence("cache_final_changed")
        except BaseException:
            with suppress(BaseException):
                self.close()
            raise BlockedEvidence("cache_reader_unavailable") from None

    def read_at(self, offset: int, count: int) -> bytes:
        if (
            type(offset) is not int
            or type(count) is not int
            or not 0 <= offset <= self._size
            or not 0 <= count <= CHUNK_BYTES
            or offset + count > self._size
        ):
            raise BlockedEvidence("cache_read_bounds")
        try:
            self.validate()
            data = os.pread(self._fd, count, offset)
            self.validate()
            if len(data) != count:
                raise BlockedEvidence("cache_short_read")
            return data
        except BaseException:
            with suppress(BaseException):
                self.close()
            raise BlockedEvidence("cache_read_failed") from None

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        failed = False
        if self._fd != -1:
            fd, self._fd = self._fd, -1
            try:
                os.close(fd)
            except BaseException:
                failed = True
        if self._owns_entry:
            try:
                self._entry.close()
            except BaseException:
                failed = True
        if failed:
            raise BlockedEvidence("cache_reader_close_failed")


class FinalModelCache:
    """One read-only final asset set. Approval/registration remains the caller's gate.

    A fresh instance is required for each load. All final files verify before a mapping
    is exposed, with duplicate-content path labels sharing one lock/reader. A failed
    open closes everything and cannot be retried on this instance.
    """

    def __init__(
        self,
        root: Path,
        repository_root: Path,
        preparation: PreparationManifest,
        inference: InferenceManifest,
    ) -> None:
        bind_inference(preparation, inference)
        self._manifest = inference
        self._assets: dict[Identity, Asset] = {}
        self._paths: dict[str, Identity] = {}
        for asset in inference.converted_assets:
            identity = (inference.preparation_sha256, inference.source_revision, asset.sha256)
            if identity in self._assets and self._assets[identity].size != asset.size:
                raise BlockedEvidence("cache_asset_identity")
            self._assets[identity] = asset
            self._paths[asset.path] = identity
        self._readers: dict[Identity, VerifiedModelReader] = {}
        self._opened = False
        self.closed = False
        try:
            self._directory = _root_fd(root, repository_root, create=False)
        except BaseException:
            raise BlockedEvidence("cache_final_root_invalid") from None

    @property
    def manifest(self) -> InferenceManifest:
        return self._manifest

    def open_assets(self, cancelled: Callable[[], bool]) -> Mapping[str, VerifiedModelReader]:
        if self.closed or self._opened:
            raise BlockedEvidence("cache_reader_unavailable")
        self._opened = True
        try:
            for identity, asset in sorted(self._assets.items()):
                self._readers[identity] = VerifiedModelReader(
                    self._directory,
                    identity,
                    asset,
                    cancelled,
                )
            for reader in self._readers.values():
                reader.validate()
            return MappingProxyType({name: self._readers[key] for name, key in self._paths.items()})
        except BaseException:
            with suppress(BaseException):
                self.close()
            raise BlockedEvidence("cache_final_set_invalid") from None

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        failed = False
        for reader in self._readers.values():
            try:
                reader.close()
            except BaseException:
                failed = True
        try:
            os.close(self._directory)
        except BaseException:
            failed = True
        if failed:
            raise BlockedEvidence("cache_final_close_failed")

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
