"""Preparation-only verified source collection; never an inference manifest or loader."""

import asyncio
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Literal

from pydantic import ValidationError

from .cache_reader import MissingModelAsset, VerifiedModelReader
from .contracts import Asset, PreparationManifest, metadata_digest
from .model_cache import Identity, ModelOnlyCache
from .runtime import BlockedEvidence


class VerifiedSourceAssets:
    """Own every reader/lock; borrow the caller's cache, which remains caller-owned.

    Probing reveals missing labels only. A complete immutable mapping is exposed once,
    after every distinct file verifies. Closing revokes all borrowed readers, including
    aliases; it never removes already completed model assets or closes the parent cache.
    """

    def __init__(
        self,
        manifest: PreparationManifest,
        mode: Literal["huggingface", "modelscope"],
        cache: ModelOnlyCache,
        cancelled: Callable[[], bool],
    ) -> None:
        try:
            manifest = PreparationManifest.model_validate(manifest.model_dump())
        except (AttributeError, ValidationError):
            raise BlockedEvidence("preparation_not_allowlisted") from None
        cache.require_preparation(manifest, mode)
        mirrors = [mirror for mirror in manifest.mirrors if mirror.mode == mode]
        if len(mirrors) != 1:
            raise BlockedEvidence("preparation_not_allowlisted")
        digest = metadata_digest(manifest)
        self._manifest, self._mode, self._cache = manifest, mode, cache
        self._cancelled = cancelled
        self._assets: dict[Identity, Asset] = {}
        self._paths: dict[str, Identity] = {}
        for asset in manifest.source_assets:
            identity = (digest, mirrors[0].revision, asset.sha256)
            if identity in self._assets and self._assets[identity].size != asset.size:
                raise BlockedEvidence("cache_asset_identity")
            self._assets.setdefault(identity, asset)
            self._paths[asset.path] = identity
        self._readers: dict[Identity, VerifiedModelReader] = {}
        self._probed = self._exposed = self.closed = False

    def _check(self) -> None:
        if self.closed:
            raise BlockedEvidence("source_collection_closed")
        self._cache.require_preparation(self._manifest, self._mode)
        if self._cancelled():
            raise asyncio.CancelledError

    def missing_assets(self) -> tuple[Asset, ...]:
        if self._probed or self._exposed:
            raise BlockedEvidence("source_collection_started")
        self._probed = True
        try:
            return self._scan(allow_missing=True)
        except BaseException:
            self.close()
            raise

    def _scan(self, *, allow_missing: bool) -> tuple[Asset, ...]:
        missing = []
        self._check()
        for identity, asset in sorted(self._assets.items()):
            self._check()
            if identity not in self._readers:
                try:
                    self._readers[identity] = self._cache.open_verified_source(
                        identity, self._cancelled
                    )
                except MissingModelAsset:
                    if not allow_missing:
                        raise BlockedEvidence("source_collection_incomplete") from None
                    missing.append(asset)
        for reader in self._readers.values():
            self._check()
            reader.validate()
        self._check()
        return tuple(missing)

    def open_assets(self) -> Mapping[str, VerifiedModelReader]:
        if self._exposed:
            raise BlockedEvidence("source_collection_started")
        try:
            self._scan(allow_missing=False)
            self._exposed = True
            return MappingProxyType({path: self._readers[key] for path, key in self._paths.items()})
        except BaseException:
            self.close()
            raise

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
        self._readers.clear()
        if failed:
            raise BlockedEvidence("source_collection_close_failed")
