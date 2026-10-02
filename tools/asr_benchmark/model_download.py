"""One explicit model-asset preparation, bounded across connect, headers and body.

The CLI registry remains empty. This internal seam accepts reviewed manifests/cache
objects, never server URLs or execution instructions. Tests use ordinary text only.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import partial
from typing import Literal

from .contracts import NS, PreparationManifest
from .http_transfer import (
    CHUNK_LIMIT,
    DownloadFailure,
    HTTPSResponse,
    ModelResponse,
    model_request,
    validate_response,
)
from .model_cache import ModelCacheEntry, ModelOnlyCache
from .preparation import PreparationTransfer, TransferProgress
from .runtime import BlockedEvidence


def _close_response(response: ModelResponse) -> None:
    try:
        response.close()
    except BaseException:
        raise DownloadFailure("download_close_failed") from None


async def _bounded[T](
    transfer: PreparationTransfer, clock: Callable[[], int], operation: Callable[[], Awaitable[T]]
) -> T:
    """One absolute progress deadline, including a check before accepting a late result."""
    try:
        now = clock()
        transfer.check(now)
        remaining = (transfer.last_progress_ns + 60 * NS - now) / NS
        timeout = asyncio.timeout(remaining)
        async with timeout:
            result = await operation()
        task = asyncio.current_task()
        if task is not None and task.cancelling():
            raise asyncio.CancelledError
        if timeout.expired():
            raise TimeoutError
        transfer.check(clock())
        return result
    except TimeoutError:
        raise DownloadFailure("transfer_no_progress", "no_progress") from None
    except BlockedEvidence as error:
        if str(error) == "transfer_no_progress":
            raise DownloadFailure("transfer_no_progress", "no_progress") from None
        raise


async def _retry(
    transfer: PreparationTransfer,
    entry: ModelCacheEntry,
    clock: Callable[[], int],
    sleep: Callable[[float], Awaitable[None]],
) -> None:
    if transfer.retry_at_ns is None:
        return
    delay = max(0, transfer.retry_at_ns - clock()) / NS
    await sleep(delay)
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise asyncio.CancelledError
    transfer.resume(transfer.identity, clock())
    # Persist the started attempt before another network request can be emitted.
    entry.save_checkpoint(transfer.checkpoint())


async def download_asset(
    manifest: PreparationManifest,
    mode: Literal["huggingface", "modelscope"],
    asset_path: str,
    cache: ModelOnlyCache,
    *,
    response_factory: Callable[[], ModelResponse] = HTTPSResponse,
    clock: Callable[[], int] = time.monotonic_ns,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    progress: Callable[[TransferProgress], None] | None = None,
) -> TransferProgress:
    """Verify/promote one manifest asset; no mirrors, headers or URLs come from callers.

    Cancellation closes the response and locked entry synchronously. An interrupted
    partial survives only if its explicit persisted checkpoint still matches actual
    length/identity/attempt count. All other failures invalidate the partial.
    """
    transfer = PreparationTransfer(manifest, mode, asset_path, clock())
    # Endpoint admission happens before opening a cache entry or allocating a transport.
    model_request(manifest, mode, asset_path, 0)
    if cache.mode != mode:
        raise BlockedEvidence("cache_identity_denied")
    entry = cache.entry(transfer.identity)
    response: ModelResponse | None = None
    try:
        offset = entry.offset()
        checkpoint = entry.checkpoint_if_present()
        if checkpoint is None:
            if offset:
                raise BlockedEvidence("checkpoint_missing")
            entry.save_checkpoint(transfer.checkpoint())
        else:
            transfer.restore_checkpoint(checkpoint, clock())
        while True:
            await _retry(transfer, entry, clock, sleep)
            if transfer.received == transfer.asset.size:
                return transfer.promote(entry, clock())
            request = model_request(manifest, mode, asset_path, entry.offset())
            if request.offset != transfer.received:
                raise BlockedEvidence("checkpoint_offset")
            try:
                response = response_factory()
                header = await _bounded(transfer, clock, partial(response.start, request))
                validate_response(header, request)
                while transfer.received < transfer.asset.size:
                    limit = min(CHUNK_LIMIT, transfer.asset.size - transfer.received)
                    chunk = await _bounded(transfer, clock, partial(response.read, limit))
                    if type(chunk) is not bytes or len(chunk) > limit:
                        raise DownloadFailure("download_body_invalid")
                    if not chunk:
                        raise DownloadFailure("download_body_truncated", "transient")
                    entry.append_model_chunk(chunk, transfer.received)
                    item = transfer.advance(entry.offset(), clock())
                    entry.save_checkpoint(transfer.checkpoint())
                    if progress is not None:
                        progress(item)
                # Connection: close plus an exact EOF check rejects an overlong payload.
                # No HTTP request is ever issued with a Range beginning at EOF.
                extra = await _bounded(transfer, clock, partial(response.read, 1))
                if type(extra) is not bytes or extra:
                    raise DownloadFailure("download_body_excess")
            except DownloadFailure as error:
                item = transfer.failure(error.kind, clock())
                if progress is not None:
                    progress(item)
                if transfer.stopped:
                    raise
            finally:
                if response is not None:
                    closing = response
                    response = None
                    _close_response(closing)
            if transfer.retry_at_ns is None:
                return transfer.promote(entry, clock())
    except asyncio.CancelledError:
        try:
            # Never manufacture a new checkpoint after a failed/half-finished write.
            saved = entry.load_checkpoint()
            if saved != transfer.checkpoint():
                raise BlockedEvidence("checkpoint_invalid")
        except BaseException:
            with suppress(BaseException):
                entry.invalidate_partial(transfer.identity)
        raise
    except BaseException as error:
        with suppress(BaseException):
            entry.invalidate_partial(transfer.identity)
        if isinstance(error, BlockedEvidence):
            raise
        raise BlockedEvidence("download_failed") from None
    finally:
        # No awaited cleanup, so repeated task cancellation cannot abandon a live entry.
        try:
            if response is not None:
                _close_response(response)
        finally:
            entry.close()
