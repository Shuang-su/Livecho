"""Fail-closed transport defaults must not open sockets when a factory is omitted."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Never

import pytest

from tools.asr_benchmark.http_transfer import transport_not_injected
from tools.asr_benchmark.model_cache import ModelOnlyCache
from tools.asr_benchmark.model_download import download_asset
from tools.asr_benchmark.preparation_run import prepare_sources
from tools.asr_benchmark.runtime import BlockedEvidence

from .factories import preparation
from .test_model_cache import NOTICE, manifest


def test_transport_not_injected_raises_before_any_socket() -> None:
    with pytest.raises(BlockedEvidence, match="transport_not_injected"):
        transport_not_injected()


def test_download_asset_default_factory_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened = False

    async def forbid_connect(*args: object, **kwargs: object) -> Never:
        nonlocal opened
        opened = True
        raise AssertionError("default download must not open a socket")

    monkeypatch.setattr(asyncio, "open_connection", forbid_connect)
    with ModelOnlyCache(
        tmp_path.resolve() / "cache", tmp_path / "repo", manifest(), "huggingface"
    ) as cache:

        async def exercise() -> None:
            with pytest.raises(BlockedEvidence, match="transport_not_injected"):
                await download_asset(manifest(), "huggingface", "NOTICE.txt", cache)

        asyncio.run(exercise())
    assert not opened


def test_prepare_sources_default_factory_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened = False

    async def forbid_connect(*args: object, **kwargs: object) -> Never:
        nonlocal opened
        opened = True
        raise AssertionError("default prepare_sources must not open a socket")

    monkeypatch.setattr(asyncio, "open_connection", forbid_connect)
    with ModelOnlyCache(
        tmp_path.resolve() / "cache", tmp_path / "repo", preparation(), "huggingface"
    ) as cache:

        async def exercise() -> None:
            with pytest.raises(BlockedEvidence, match="transport_not_injected"):
                async with prepare_sources(preparation(), "huggingface", cache):
                    raise AssertionError("scope must not open without injected transport")

        asyncio.run(exercise())
    assert not opened


def test_same_size_mtime_restored_partial_refuses_promotion(
    tmp_path: Path,
) -> None:
    """Content re-hash catches same-size writes when mtime is restored (coarse FS)."""
    import os

    from .test_model_cache import complete, path, transfer

    with (
        ModelOnlyCache(
            tmp_path.resolve() / "cache", tmp_path / "repo", manifest(), "huggingface"
        ) as cache,
        cache.entry(transfer().identity) as entry,
    ):
        identity = complete(entry)
        partial = path(tmp_path, "partial")
        before = os.stat(partial)
        with partial.open("r+b") as stream:
            stream.write(b"X" * min(8, len(NOTICE)))
        os.utime(partial, ns=(before.st_atime_ns, before.st_mtime_ns))
        with pytest.raises(BlockedEvidence, match="cache_promotion_failed"):
            entry.atomic_promote(identity)
    assert not path(tmp_path, "asset").exists()
