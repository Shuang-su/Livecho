"""Coordinator faults use an original notice and in-process IO doubles only."""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest

from tools.asr_benchmark.contracts import NS
from tools.asr_benchmark.http_transfer import (
    DownloadFailure,
    HTTPSResponse,
    ModelRequest,
    ModelResponse,
)
from tools.asr_benchmark.model_cache import ModelCacheEntry, ModelOnlyCache
from tools.asr_benchmark.model_download import download_asset
from tools.asr_benchmark.preparation import TransferProgress
from tools.asr_benchmark.runtime import BlockedEvidence

from .test_http_transfer import Reader, Writer
from .test_model_cache import NOTICE, manifest, path, transfer


@pytest.fixture
def cache(tmp_path: Path) -> Iterator[ModelOnlyCache]:
    with ModelOnlyCache(
        tmp_path.resolve() / "cache", tmp_path / "repo", manifest(), "huggingface"
    ) as value:
        yield value


class Clock:
    def __init__(self) -> None:
        self.now = 0
        self.delays: list[float] = []

    def __call__(self) -> int:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.delays.append(seconds)
        self.now += int(seconds * NS)


class Response:
    def __init__(
        self,
        *,
        status: int | None = None,
        chunks: list[bytes] | None = None,
        clock: Clock | None = None,
        start_ns: int = 0,
        read_ns: int = 0,
    ) -> None:
        self.status, self.chunks = status, chunks
        self.clock, self.start_ns, self.read_ns = clock, start_ns, read_ns
        self.closed = False
        self.requests: list[ModelRequest] = []
        self.reads: list[int] = []
        self.remaining = b""

    async def start(self, request: ModelRequest) -> bytes:
        self.requests.append(request)
        self.remaining = NOTICE[request.offset :]
        if self.clock is not None:
            self.clock.now += self.start_ns
        status = self.status or (206 if request.offset else 200)
        suffix = (
            f"Content-Range: bytes {request.offset}-{len(NOTICE) - 1}/{len(NOTICE)}\r\n"
            if request.offset
            else ""
        )
        return (
            f"HTTP/1.1 {status} Test\r\nContent-Length: {len(self.remaining)}\r\n{suffix}\r\n"
        ).encode()

    async def read(self, limit: int) -> bytes:
        assert not self.closed
        self.reads.append(limit)
        if self.clock is not None:
            self.clock.now += self.read_ns
        if self.chunks is not None:
            return self.chunks.pop(0) if self.chunks else b""
        value, self.remaining = self.remaining[:limit], self.remaining[limit:]
        return value

    def close(self) -> None:
        self.closed = True


class Factory:
    def __init__(self, *responses: Response) -> None:
        self.responses = list(responses)
        self.created: list[Response] = []

    def __call__(self) -> ModelResponse:
        # A replacement may only be allocated after the previous response was revoked.
        assert all(response.closed for response in self.created)
        response = self.responses.pop(0)
        self.created.append(response)
        return response


async def run(cache: ModelOnlyCache, factory: Factory, clock: Clock) -> TransferProgress:
    return await download_asset(
        manifest(),
        "huggingface",
        "NOTICE.txt",
        cache,
        response_factory=factory,
        clock=clock,
        sleep=clock.sleep,
    )


def test_fresh_exact_download_verifies_actual_hash_and_promotes(
    cache: ModelOnlyCache, tmp_path: Path
) -> None:
    response = Response()
    result = asyncio.run(run(cache, Factory(response), Clock()))
    assert result.outcome == "verified" and result.received == len(NOTICE)
    assert response.closed and response.reads[-1] == 1
    assert path(tmp_path, "asset").read_bytes() == NOTICE
    assert not path(tmp_path, "partial").exists()
    assert not path(tmp_path, "checkpoint").exists()


def test_truncation_resumes_actual_offset_and_waits_exact_retry_delay(
    cache: ModelOnlyCache,
) -> None:
    clock = Clock()
    first, second = Response(chunks=[NOTICE[:10], b""]), Response()
    result = asyncio.run(run(cache, Factory(first, second), clock))
    assert result.retry_count == 1 and clock.delays == [1.0]
    assert second.requests[0].offset == 10
    assert first.closed and second.closed


def test_third_failure_terminates_and_invalidates(cache: ModelOnlyCache, tmp_path: Path) -> None:
    clock = Clock()
    factory = Factory(*(Response(status=503) for _ in range(3)))
    with pytest.raises(DownloadFailure, match="transient"):
        asyncio.run(run(cache, factory, clock))
    assert len(factory.created) == 3 and clock.delays == [1.0, 2.0]
    assert all(r.closed for r in factory.created)
    assert not path(tmp_path, "partial").exists()
    assert not path(tmp_path, "checkpoint").exists()


@pytest.mark.parametrize("status", [401, 403, 302, 429, 404])
def test_terminal_status_never_reads_retries_or_retains_partial(
    cache: ModelOnlyCache, tmp_path: Path, status: int
) -> None:
    clock, response = Clock(), Response(status=status)
    with pytest.raises(DownloadFailure):
        asyncio.run(run(cache, Factory(response), clock))
    assert response.closed and not response.reads and not clock.delays
    assert not path(tmp_path, "partial").exists()


@pytest.mark.parametrize("kind", ["excess", "oversized", "corrupt"])
def test_payload_integrity_fails_closed(cache: ModelOnlyCache, tmp_path: Path, kind: str) -> None:
    chunks = {
        "excess": [NOTICE, b"extra"],
        "oversized": [NOTICE + b"extra"],
        "corrupt": [b"X" + NOTICE[1:], b""],
    }[kind]
    response = Response(chunks=chunks)
    with pytest.raises(BlockedEvidence):
        asyncio.run(run(cache, Factory(response), Clock()))
    assert response.closed
    assert not path(tmp_path, "asset").exists()
    assert not path(tmp_path, "partial").exists()


def test_remaining_deadline_spans_headers_and_body_and_rejects_late_results(
    cache: ModelOnlyCache, tmp_path: Path
) -> None:
    clock = Clock()
    factory = Factory(*(Response(clock=clock, start_ns=40 * NS, read_ns=21 * NS) for _ in range(3)))
    with pytest.raises(DownloadFailure, match="no_progress"):
        asyncio.run(run(cache, factory, clock))
    assert [r.requests[0].offset for r in factory.created] == [0, 0, 0]
    assert clock.delays == [1.0, 2.0]
    assert not path(tmp_path, "partial").exists()


def test_only_body_progress_renews_deadline(cache: ModelOnlyCache) -> None:
    clock = Clock()
    response = Response(clock=clock, read_ns=30 * NS, chunks=[NOTICE[:10], NOTICE[10:], b""])
    result = asyncio.run(run(cache, Factory(response), clock))
    assert result.outcome == "verified" and clock.now == 90 * NS


@pytest.mark.parametrize("complete", [False, True])
def test_cancellation_retains_explicit_checkpoint_then_restores(
    cache: ModelOnlyCache, tmp_path: Path, complete: bool
) -> None:
    clock = Clock()
    first = Response(chunks=[NOTICE if complete else NOTICE[:10]])

    def cancel(item: TransferProgress) -> None:
        assert item.outcome == "partial"
        raise asyncio.CancelledError

    async def exercise() -> None:
        with pytest.raises(asyncio.CancelledError):
            await download_asset(
                manifest(),
                "huggingface",
                "NOTICE.txt",
                cache,
                response_factory=Factory(first),
                clock=clock,
                sleep=clock.sleep,
                progress=cancel,
            )
        assert first.closed and path(tmp_path, "checkpoint").exists()
        replacement = Factory() if complete else Factory(Response())
        result = await run(cache, replacement, clock)
        assert result.outcome == "verified"
        assert len(replacement.created) == (0 if complete else 1)
        assert clock.delays == ([] if complete else [1.0])

    asyncio.run(exercise())


def test_full_partial_from_last_attempt_is_verified_without_fourth_request(
    cache: ModelOnlyCache,
) -> None:
    controller = transfer()
    controller.attempt = 3
    with cache.entry(controller.identity) as entry:
        entry.append_model_chunk(NOTICE, 0)
        controller.advance(len(NOTICE), 1)
        entry.save_checkpoint(controller.checkpoint())
    result = asyncio.run(run(cache, Factory(), Clock()))
    assert result.outcome == "verified" and result.retry_count == 2


@pytest.mark.parametrize("kind", ["missing", "stale", "exhausted"])
def test_invalid_partial_cannot_reset_attempt_budget(
    cache: ModelOnlyCache, tmp_path: Path, kind: str
) -> None:
    controller = transfer()
    with cache.entry(controller.identity) as entry:
        entry.append_model_chunk(NOTICE[:10], 0)
        controller.advance(10, 1)
        if kind == "exhausted":
            controller.attempt = 3
        if kind != "missing":
            entry.save_checkpoint(controller.checkpoint())
        if kind == "stale":
            entry.append_model_chunk(NOTICE[10:11], 10)
    with pytest.raises(BlockedEvidence, match="checkpoint"):
        asyncio.run(run(cache, Factory(), Clock()))
    assert not path(tmp_path, "partial").exists()


def test_zero_offset_checkpoint_still_consumes_prior_attempt(cache: ModelOnlyCache) -> None:
    controller = transfer()
    controller.attempt = 2
    with cache.entry(controller.identity) as entry:
        entry.save_checkpoint(controller.checkpoint())
    clock = Clock()
    result = asyncio.run(run(cache, Factory(Response()), clock))
    assert result.retry_count == 2 and clock.delays == [2.0]


def test_external_cancellation_revokes_pending_io_and_releases_cache_lock(
    cache: ModelOnlyCache,
) -> None:
    async def exercise() -> None:
        started = asyncio.Event()

        class Waiting(Response):
            async def start(self, request: ModelRequest) -> bytes:
                started.set()
                await asyncio.Future[None]()
                raise AssertionError

        response = Waiting()
        task = asyncio.create_task(run(cache, Factory(response), Clock()))
        await started.wait()
        task.cancel()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert response.closed
        with cache.entry(transfer().identity) as entry:
            assert entry.offset() == 0 and entry.load_checkpoint()

    asyncio.run(exercise())


def test_suppressed_cancellation_cannot_commit_late_body(cache: ModelOnlyCache) -> None:
    async def exercise() -> None:
        started = asyncio.Event()

        class Late(Response):
            async def read(self, limit: int) -> bytes:
                started.set()
                try:
                    await asyncio.Future[None]()
                except asyncio.CancelledError:
                    return NOTICE
                raise AssertionError

        response = Late()
        task = asyncio.create_task(run(cache, Factory(response), Clock()))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert response.closed
        with cache.entry(transfer().identity) as entry:
            assert entry.offset() == 0

    asyncio.run(exercise())


def test_suppressed_start_cancellation_cannot_accept_response(cache: ModelOnlyCache) -> None:
    async def exercise() -> None:
        started = asyncio.Event()

        class Late(Response):
            async def start(self, request: ModelRequest) -> bytes:
                started.set()
                try:
                    await asyncio.Future[None]()
                except asyncio.CancelledError:
                    return await super().start(request)
                raise AssertionError

        response = Late()
        task = asyncio.create_task(run(cache, Factory(response), Clock()))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert response.closed and not response.reads
        with cache.entry(transfer().identity) as entry:
            assert entry.offset() == 0

    asyncio.run(exercise())


def test_late_connection_is_aborted_without_emitting_request(
    cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def exercise() -> None:
        started = asyncio.Event()
        reader, writer = Reader(), Writer()

        async def connect(*args: object, **kwargs: object) -> tuple[Reader, Writer]:
            started.set()
            try:
                await asyncio.Future[None]()
            except asyncio.CancelledError:
                return reader, writer
            raise AssertionError

        monkeypatch.setattr(asyncio, "open_connection", connect)
        task = asyncio.create_task(
            download_asset(
                manifest(), "huggingface", "NOTICE.txt", cache, response_factory=HTTPSResponse
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert writer.aborted and not writer.writes
        with cache.entry(transfer().identity) as entry:
            assert entry.offset() == 0

    asyncio.run(exercise())


@pytest.mark.parametrize("cancellation", [False, True])
def test_close_failure_invalidates_partial_and_still_releases_entry(
    cache: ModelOnlyCache, tmp_path: Path, cancellation: bool
) -> None:
    class FailingClose(Response):
        def close(self) -> None:
            super().close()
            if cancellation:
                raise asyncio.CancelledError
            raise RuntimeError("untrusted provider diagnostic")

    with pytest.raises(DownloadFailure, match="download_close_failed"):
        asyncio.run(run(cache, Factory(FailingClose()), Clock()))
    assert not path(tmp_path, "partial").exists()
    assert not path(tmp_path, "asset").exists()
    with cache.entry(transfer().identity) as entry:
        assert entry.offset() == 0


def test_cancellation_during_retry_preserves_attempt_budget(cache: ModelOnlyCache) -> None:
    async def exercise() -> None:
        clock = Clock()
        started = asyncio.Event()

        async def sleep(seconds: float) -> None:
            started.set()
            await asyncio.Future[None]()

        response = Response(status=503)
        task = asyncio.create_task(
            download_asset(
                manifest(),
                "huggingface",
                "NOTICE.txt",
                cache,
                response_factory=Factory(response),
                clock=clock,
                sleep=sleep,
            )
        )
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert response.closed
        result = await run(cache, Factory(Response()), clock)
        assert result.retry_count == 1 and clock.delays == [1.0]

    asyncio.run(exercise())


def test_missing_modelscope_authority_opens_neither_entry_nor_transport(
    cache: ModelOnlyCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object) -> None:
        raise AssertionError("not admitted")

    monkeypatch.setattr(cache, "entry", forbidden)
    with pytest.raises(DownloadFailure, match="endpoint_unverified"):
        asyncio.run(download_asset(manifest(), "modelscope", "NOTICE.txt", cache))


@pytest.mark.parametrize("after_save", [False, True])
def test_cancellation_at_checkpoint_commit_preserves_only_matching_partial(
    cache: ModelOnlyCache, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_save: bool
) -> None:
    original = ModelCacheEntry.save_checkpoint
    calls = 0

    def save(entry: ModelCacheEntry, text: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2 and not after_save:
            raise asyncio.CancelledError
        original(entry, text)
        if calls == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(ModelCacheEntry, "save_checkpoint", save)
    response = Response(chunks=[NOTICE[:10]])
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run(cache, Factory(response), Clock()))
    assert response.closed
    assert path(tmp_path, "partial").exists() == after_save
    assert path(tmp_path, "checkpoint").exists() == after_save
    with cache.entry(transfer().identity) as entry:
        assert entry.offset() == (10 if after_save else 0)


def test_real_async_deadline_cancels_stalled_read(cache: ModelOnlyCache) -> None:
    controller = transfer()
    controller.attempt = 2
    with cache.entry(controller.identity) as entry:
        entry.save_checkpoint(controller.checkpoint())
    clock = Clock()

    class Stalled(Response):
        cancelled = False

        async def start(self, request: ModelRequest) -> bytes:
            result = await super().start(request)
            clock.now += 60 * NS - 10_000_000
            return result

        async def read(self, limit: int) -> bytes:
            try:
                await asyncio.Future[None]()
            except asyncio.CancelledError:
                self.cancelled = True
                # Even a swallowed deadline cancellation may not yield usable data.
                return NOTICE
            raise AssertionError

    response = Stalled()
    with pytest.raises(DownloadFailure, match="no_progress"):
        asyncio.run(run(cache, Factory(response), clock))
    assert response.cancelled and response.closed
    assert clock.delays == [2.0]
    with cache.entry(controller.identity) as entry:
        assert entry.offset() == 0
