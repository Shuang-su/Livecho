"""Original notice text and transport doubles only; no real model/network/audio IO."""

import asyncio
import hashlib
import os
from collections.abc import Iterator, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Literal

import pytest

from tools.asr_benchmark import preparation_run
from tools.asr_benchmark.cache_reader import MissingModelAsset, VerifiedModelReader
from tools.asr_benchmark.contracts import Asset, PreparationManifest, metadata_digest
from tools.asr_benchmark.http_transfer import DownloadFailure, ModelRequest, ModelResponse
from tools.asr_benchmark.model_cache import Identity, ModelOnlyCache
from tools.asr_benchmark.model_download import download_asset
from tools.asr_benchmark.preparation import PreparationTransfer, TransferProgress
from tools.asr_benchmark.preparation_run import prepare_sources
from tools.asr_benchmark.runtime import BlockedEvidence
from tools.asr_benchmark.source_cache import VerifiedSourceAssets

from .factories import preparation
from .test_model_download import Clock

Mode = Literal["huggingface", "modelscope"]
TEXTS = (
    b"Original source collection notice A; ordinary text, no model or audio.\n",
    b"Original source collection notice B; ordinary text, no model or audio.\n",
)


def manifest() -> PreparationManifest:
    base = preparation()
    assets = tuple(
        asset.model_copy(
            update={"size": len(TEXTS[i % 2]), "sha256": hashlib.sha256(TEXTS[i % 2]).hexdigest()}
        )
        for i, asset in enumerate(base.source_assets)
    )
    mirrors = tuple(
        mirror.model_copy(
            update={
                "assets": assets,
                "revision": "b" * 40 if mirror.mode == "modelscope" else mirror.revision,
            }
        )
        for mirror in base.mirrors
    )
    return PreparationManifest.model_validate(
        base.model_copy(update={"source_assets": assets, "mirrors": mirrors}).model_dump()
    )


def identity(asset: Asset, mode: Mode = "huggingface") -> Identity:
    record = manifest()
    mirror = next(m for m in record.mirrors if m.mode == mode)
    return metadata_digest(record), mirror.revision, asset.sha256


def file_path(tmp_path: Path, asset: Asset, mode: Mode = "huggingface") -> Path:
    key = hashlib.sha256("|".join(identity(asset, mode)).encode()).hexdigest()
    return tmp_path / "cache" / f"{key}.asset"


def content(asset: Asset) -> bytes:
    return next(text for text in TEXTS if hashlib.sha256(text).hexdigest() == asset.sha256)


def populate(cache: ModelOnlyCache, assets: tuple[Asset, ...] | None = None) -> None:
    unique = {a.sha256: a for a in (assets if assets is not None else manifest().source_assets)}
    for asset in unique.values():
        with cache.entry(identity(asset, cache.mode)) as entry:
            entry.append_model_chunk(content(asset), 0)
            entry.inspect_partial(entry.identity)
            entry.atomic_promote(entry.identity)


def assert_unlocked(cache: ModelOnlyCache) -> None:
    for asset in manifest().source_assets:
        with cache.entry(identity(asset, cache.mode)):
            pass


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[ModelOnlyCache]:
    with ModelOnlyCache(
        tmp_path.resolve() / "cache", tmp_path / "repo", manifest(), "huggingface"
    ) as value:
        yield value


class Response:
    def __init__(self) -> None:
        self.request: ModelRequest | None = None
        self.remaining = b""
        self.closed = False

    async def start(self, request: ModelRequest) -> bytes:
        self.request = request
        self.remaining = content(request.asset)[request.offset :]
        suffix = (
            f"Content-Range: bytes {request.offset}-"
            f"{request.asset.size - 1}/{request.asset.size}\r\n"
            if request.offset
            else ""
        )
        return (
            f"HTTP/1.1 {206 if request.offset else 200} Test\r\n"
            f"Content-Length: {len(self.remaining)}\r\n{suffix}\r\n"
        ).encode()

    async def read(self, limit: int) -> bytes:
        assert not self.closed
        chunk, self.remaining = self.remaining[:limit], self.remaining[limit:]
        return chunk

    def close(self) -> None:
        self.closed = True


class Factory:
    def __init__(self) -> None:
        self.responses: list[Response] = []

    def __call__(self) -> ModelResponse:
        assert all(response.closed for response in self.responses)
        response = Response()
        self.responses.append(response)
        return response


def test_complete_cache_reused_and_borrows_revoked(cache: ModelOnlyCache) -> None:
    populate(cache)
    factory = Factory()

    async def exercise() -> None:
        async with prepare_sources(
            manifest(), "huggingface", cache, response_factory=factory
        ) as assets:
            assert set(assets) == {a.path for a in manifest().source_assets}
            assert len(set(assets.values())) == 2
            assert assets["model.safetensors"] is assets["config.json"]
            for asset in manifest().source_assets:
                reader = assets[asset.path]
                assert reader.read_at(3, 6) == content(asset)[3:9]
                assert reader.read_at(0, 2) == content(asset)[:2]
                assert not hasattr(reader, "path") and not hasattr(reader, "fileno")
            with pytest.raises(TypeError):
                assets["other"] = assets["config.json"]  # type: ignore[index]
        for reader in assets.values():
            with pytest.raises(BlockedEvidence):
                reader.read_at(0, 1)

    asyncio.run(exercise())
    assert not factory.responses and not cache.closed
    assert_unlocked(cache)


@pytest.mark.parametrize("prepopulate", [False, True])
def test_only_missing_physical_assets_downloaded_and_all_verified_before_delivery(
    cache: ModelOnlyCache, prepopulate: bool
) -> None:
    if prepopulate:
        populate(cache, manifest().source_assets[:1])
    factory = Factory()
    clock = Clock()

    async def exercise() -> None:
        async with prepare_sources(
            manifest(),
            "huggingface",
            cache,
            response_factory=factory,
            clock=clock,
            sleep=clock.sleep,
        ) as assets:
            assert len(assets) == 4 and len(set(assets.values())) == 2
            for asset in manifest().source_assets:
                assert assets[asset.path].read_at(0, asset.size) == content(asset)

    asyncio.run(exercise())
    requests = [r.request for r in factory.responses if r.request]
    assert len(requests) == (1 if prepopulate else 2)
    assert len({r.asset.sha256 for r in requests}) == len(requests)
    assert all(r.revision == manifest().source_revision and r.offset == 0 for r in requests)
    assert not clock.delays
    assert_unlocked(cache)


@pytest.mark.parametrize(
    "kind", ["short", "corrupt", "symlink", "dangling", "hardlink", "fifo", "public"]
)
def test_invalid_final_is_terminal_without_downloading(
    cache: ModelOnlyCache, tmp_path: Path, kind: str
) -> None:
    populate(cache)
    asset = manifest().source_assets[1]
    target = file_path(tmp_path, asset)
    target.unlink()
    if kind in {"short", "corrupt", "public"}:
        target.write_bytes(content(asset)[:2] if kind == "short" else b"x" * asset.size)
        target.chmod(0o644 if kind == "public" else 0o600)
    elif kind in {"symlink", "dangling", "hardlink"}:
        other = tmp_path / "ordinary-notice"
        if kind != "dangling":
            other.write_bytes(content(asset))
            other.chmod(0o600)
        if kind == "hardlink":
            os.link(other, target)
        else:
            target.symlink_to(other)
    else:
        os.mkfifo(target, 0o600)
    factory = Factory()

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence):
            async with prepare_sources(manifest(), "huggingface", cache, response_factory=factory):
                pytest.fail("invalid set exposed")

    asyncio.run(exercise())
    assert not factory.responses
    assert_unlocked(cache)


def test_locked_asset_is_not_missing(cache: ModelOnlyCache) -> None:
    populate(cache)
    factory = Factory()

    async def exercise() -> None:
        with (
            cache.entry(identity(manifest().source_assets[1])),
            pytest.raises(BlockedEvidence, match="cache_lock_unavailable"),
        ):
            async with prepare_sources(manifest(), "huggingface", cache, response_factory=factory):
                pytest.fail("locked set exposed")

    asyncio.run(exercise())
    assert not factory.responses
    assert_unlocked(cache)


def test_cache_preparation_and_mode_binding_precedes_probe(cache: ModelOnlyCache) -> None:
    changed = manifest().model_copy(update={"manifest_id": "different-preparation"})
    for record, mode in ((changed, "huggingface"), (manifest(), "modelscope")):
        with pytest.raises(BlockedEvidence, match="cache_identity_denied"):
            VerifiedSourceAssets(record, mode, cache, lambda: False)  # type: ignore[arg-type]
    assert_unlocked(cache)


def test_selected_mirror_revision_used_for_cached_assets_and_missing_ms_is_blocked(
    tmp_path: Path,
) -> None:
    with ModelOnlyCache(
        tmp_path.resolve() / "cache", tmp_path / "repo", manifest(), "modelscope"
    ) as cache:
        factory = Factory()

        async def missing() -> None:
            with pytest.raises(DownloadFailure, match="endpoint_unverified"):
                async with prepare_sources(
                    manifest(), "modelscope", cache, response_factory=factory
                ):
                    pytest.fail("missing ModelScope downloaded")

        asyncio.run(missing())
        populate(cache)
        assert all(file_path(tmp_path, a, "modelscope").exists() for a in manifest().source_assets)
        assert not file_path(tmp_path, manifest().source_assets[0], "huggingface").exists()

        async def cached() -> None:
            async with prepare_sources(
                manifest(), "modelscope", cache, response_factory=factory
            ) as assets:
                for asset in manifest().source_assets:
                    assert assets[asset.path].read_at(0, asset.size) == content(asset)

        asyncio.run(cached())
        assert not factory.responses
        assert_unlocked(cache)


@pytest.mark.parametrize("fake_writes", [False, True])
def test_downloader_claim_cannot_replace_actual_file_verification(
    cache: ModelOnlyCache, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fake_writes: bool
) -> None:
    async def fake(
        manifest: PreparationManifest,
        mode: Mode,
        path: str,
        cache: ModelOnlyCache,
        **kwargs: object,
    ) -> TransferProgress:
        asset = next(a for a in manifest.source_assets if a.path == path)
        if fake_writes:
            target = file_path(tmp_path, asset)
            target.write_bytes(b"x" * asset.size)
            target.chmod(0o600)
        return TransferProgress(path, asset.size, asset.size, 100.0, 0, "verified")

    monkeypatch.setattr(preparation_run, "download_asset", fake)

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence):
            async with prepare_sources(manifest(), "huggingface", cache):
                pytest.fail("unverified downloader claim exposed")

    asyncio.run(exercise())
    assert_unlocked(cache)


def test_final_completed_between_probe_and_download_is_verified_and_reused(
    cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = download_asset
    factory = Factory()

    async def race(
        record: PreparationManifest,
        mode: Mode,
        path: str,
        selected: ModelOnlyCache,
        **kwargs: object,
    ) -> TransferProgress:
        asset = next(a for a in record.source_assets if a.path == path)
        populate(selected, (asset,))
        return await original(record, mode, path, selected, response_factory=factory)

    monkeypatch.setattr(preparation_run, "download_asset", race)

    async def exercise() -> None:
        async with prepare_sources(manifest(), "huggingface", cache) as assets:
            assert len(assets) == 4

    asyncio.run(exercise())
    assert not factory.responses
    assert_unlocked(cache)


def test_borrowed_reader_does_not_release_entry_lock_including_missing(
    cache: ModelOnlyCache,
) -> None:
    asset = manifest().source_assets[0]
    with cache.entry(identity(asset)) as entry:
        with pytest.raises(MissingModelAsset):
            VerifiedModelReader.from_entry(entry, lambda: False, owns_entry=False)
        assert not entry.closed
        with pytest.raises(BlockedEvidence, match="cache_lock_unavailable"):
            cache.entry(identity(asset))
    populate(cache)
    with cache.entry(identity(asset)) as entry:
        reader = VerifiedModelReader.from_entry(entry, lambda: False, owns_entry=False)
        reader.close()
        assert not entry.closed
        with pytest.raises(BlockedEvidence, match="cache_lock_unavailable"):
            cache.entry(identity(asset))
    assert_unlocked(cache)


def test_failure_on_last_download_releases_earlier_readers_and_keeps_valid_cache(
    cache: ModelOnlyCache, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = manifest().source_assets[0]
    populate(cache, (first,))

    async def fail(*args: object, **kwargs: object) -> TransferProgress:
        raise DownloadFailure("download_permission", "permission")

    monkeypatch.setattr(preparation_run, "download_asset", fail)

    async def exercise() -> None:
        with pytest.raises(DownloadFailure, match="permission"):
            async with prepare_sources(manifest(), "huggingface", cache):
                pytest.fail("partial collection exposed")

    asyncio.run(exercise())
    assert file_path(tmp_path, first).read_bytes() == content(first)
    assert_unlocked(cache)


def test_cancellation_after_last_await_prevents_delivery(
    cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    count = 0

    async def fake(
        record: PreparationManifest,
        mode: Mode,
        path: str,
        selected: ModelOnlyCache,
        **kwargs: object,
    ) -> TransferProgress:
        nonlocal count
        asset = next(a for a in record.source_assets if a.path == path)
        populate(selected, (asset,))
        count += 1
        if count == 2:
            task = asyncio.current_task()
            assert task is not None
            task.cancel()
        return TransferProgress(path, asset.size, asset.size, 100.0, 0, "verified")

    monkeypatch.setattr(preparation_run, "download_asset", fake)

    async def exercise() -> None:
        async with prepare_sources(manifest(), "huggingface", cache):
            pytest.fail("cancelled collection exposed")

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise())
    assert count == 2
    assert_unlocked(cache)


def test_consumer_cancellation_revokes_every_borrow(cache: ModelOnlyCache) -> None:
    populate(cache)
    retained: Mapping[str, VerifiedModelReader] = {}

    async def exercise() -> None:
        nonlocal retained
        async with prepare_sources(manifest(), "huggingface", cache) as assets:
            retained = assets
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise())
    assert all(reader.closed for reader in retained.values())
    assert_unlocked(cache)


def test_cancel_flag_on_late_network_result_never_writes_body(cache: ModelOnlyCache) -> None:
    cancel = False

    class Late(Response):
        async def read(self, limit: int) -> bytes:
            nonlocal cancel
            cancel = True
            return await super().read(limit)

    response = Late()

    async def exercise() -> None:
        async with prepare_sources(
            manifest(),
            "huggingface",
            cache,
            response_factory=lambda: response,
            cancelled=lambda: cancel,
        ):
            pytest.fail("cancelled read exposed")

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise())
    assert response.closed and response.request is not None
    with cache.entry(identity(response.request.asset)) as entry:
        assert entry.offset() == 0 and entry.load_checkpoint()
    assert_unlocked(cache)


def test_reader_cleanup_failure_still_attempts_every_close(
    cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    populate(cache)
    original = VerifiedModelReader.close
    closed: list[VerifiedModelReader] = []

    def close(reader: VerifiedModelReader) -> None:
        original(reader)
        closed.append(reader)
        if len(closed) == 1:
            raise asyncio.CancelledError

    monkeypatch.setattr(VerifiedModelReader, "close", close)

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence, match="source_collection_close_failed"):
            async with prepare_sources(manifest(), "huggingface", cache):
                pass

    asyncio.run(exercise())
    assert len(closed) == 2
    assert_unlocked(cache)


def test_progress_cancellation_prevents_next_chunk_and_retains_matching_partial(
    cache: ModelOnlyCache,
) -> None:
    cancel = False

    class Chunks(Response):
        reads = 0

        async def read(self, limit: int) -> bytes:
            self.reads += 1
            return await super().read(min(limit, 10))

    response = Chunks()

    def progress(item: TransferProgress) -> None:
        nonlocal cancel
        assert item.received == 10
        cancel = True

    async def exercise() -> None:
        async with prepare_sources(
            manifest(),
            "huggingface",
            cache,
            response_factory=lambda: response,
            progress=progress,
            cancelled=lambda: cancel,
        ):
            pytest.fail("cancelled set exposed")

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise())
    assert response.closed and response.reads == 1 and response.request is not None
    with cache.entry(identity(response.request.asset)) as entry:
        assert entry.offset() == 10 and entry.load_checkpoint()
    assert_unlocked(cache)


@pytest.mark.parametrize("complete_partial", [False, True])
def test_direct_download_local_completion_rejects_pending_task_cancellation(
    cache: ModelOnlyCache, complete_partial: bool
) -> None:
    asset = manifest().source_assets[0]
    if complete_partial:
        controller = PreparationTransfer(manifest(), "huggingface", asset.path, 0)
        with cache.entry(controller.identity) as entry:
            entry.append_model_chunk(content(asset), 0)
            controller.advance(asset.size, 1)
            entry.save_checkpoint(controller.checkpoint())
    else:
        populate(cache, (asset,))
    factory = Factory()
    delivered = False

    async def exercise() -> None:
        nonlocal delivered
        task = asyncio.current_task()
        assert task is not None
        task.cancel()
        with suppress(asyncio.CancelledError):
            await asyncio.sleep(0)
        await download_asset(manifest(), "huggingface", asset.path, cache, response_factory=factory)
        delivered = True

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise())
    assert not delivered and not factory.responses
    assert_unlocked(cache)


def test_cached_collection_cancelled_before_delivery(cache: ModelOnlyCache) -> None:
    populate(cache)
    factory = Factory()

    async def exercise() -> None:
        async with prepare_sources(
            manifest(),
            "huggingface",
            cache,
            response_factory=factory,
            cancelled=lambda: True,
        ):
            pytest.fail("cancelled cached set exposed")

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise())
    assert not factory.responses
    assert_unlocked(cache)


def test_changed_probed_reader_prevents_complete_set_delivery(
    cache: ModelOnlyCache, tmp_path: Path
) -> None:
    populate(cache)
    owner = VerifiedSourceAssets(manifest(), "huggingface", cache, lambda: False)
    assert owner.missing_assets() == ()
    file_path(tmp_path, manifest().source_assets[0]).write_bytes(b"changed ordinary notice")
    with pytest.raises(BlockedEvidence):
        owner.open_assets()
    assert owner.closed
    assert_unlocked(cache)


def test_conflicting_alias_size_fails_before_opening_cache(tmp_path: Path) -> None:
    record = manifest()
    assets = list(record.source_assets)
    assets[2] = assets[2].model_copy(update={"size": assets[2].size + 1})
    changed = record.model_copy(
        update={
            "source_assets": tuple(assets),
            "mirrors": tuple(
                m.model_copy(update={"assets": tuple(assets)}) for m in record.mirrors
            ),
        }
    )
    with pytest.raises(BlockedEvidence, match="cache_asset_identity"):
        ModelOnlyCache(tmp_path.resolve() / "cache", tmp_path / "repo", changed, "huggingface")
    assert not (tmp_path / "cache").exists()


def test_os_permission_error_is_not_missing(
    cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = os.open
    factory = Factory()

    def denied(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if str(path).endswith(".asset"):
            raise PermissionError("private host detail")
        return original(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", denied)

    async def exercise() -> None:
        with pytest.raises(BlockedEvidence, match="cache_final_invalid"):
            async with prepare_sources(manifest(), "huggingface", cache, response_factory=factory):
                pytest.fail("permission denial treated as missing")

    asyncio.run(exercise())
    assert not factory.responses
    assert_unlocked(cache)
