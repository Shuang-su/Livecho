"""Acquire only missing preparation assets, then lend the fully verified source set."""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from typing import Literal

from .cache_reader import VerifiedModelReader
from .contracts import PreparationManifest
from .http_transfer import HTTPSResponse, ModelResponse
from .model_cache import ModelOnlyCache
from .model_download import download_asset
from .preparation import TransferProgress
from .source_cache import VerifiedSourceAssets


@asynccontextmanager
async def prepare_sources(
    manifest: PreparationManifest,
    mode: Literal["huggingface", "modelscope"],
    cache: ModelOnlyCache,
    *,
    response_factory: Callable[[], ModelResponse] = HTTPSResponse,
    clock: Callable[[], int] = time.monotonic_ns,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    progress: Callable[[TransferProgress], None] | None = None,
    cancelled: Callable[[], bool] = lambda: False,
) -> AsyncIterator[Mapping[str, VerifiedModelReader]]:
    """No conversion/inference authority or CLI registration is created by this scope.

    The caller owns cache; this context owns and revokes all source readers. Completed
    files remain cached after cancellation; the downloader owns partial/checkpoint rules.
    """

    def is_cancelled() -> bool:
        task = asyncio.current_task()
        return cancelled() or (task is not None and task.cancelling() > 0)

    owner = VerifiedSourceAssets(manifest, mode, cache, is_cancelled)
    try:
        for asset in owner.missing_assets():
            if is_cancelled():
                raise asyncio.CancelledError
            await download_asset(
                manifest,
                mode,
                asset.path,
                cache,
                response_factory=response_factory,
                clock=clock,
                sleep=sleep,
                progress=progress,
                cancelled=is_cancelled,
            )
            if is_cancelled():
                raise asyncio.CancelledError
        # Includes cancellation after the last await and before any handle escapes.
        assets = owner.open_assets()
        if is_cancelled():
            raise asyncio.CancelledError
        yield assets
    finally:
        owner.close()
