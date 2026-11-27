"""Model acquisition (allowlisted HTTPS + redirects) and affine 8-bit group-64 conversion."""

from __future__ import annotations

import asyncio
import concurrent.futures
import http.client
import io
import ssl
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote, urlparse

from .cache_reader import MissingModelAsset, VerifiedModelReader
from .contracts import InferenceManifest, PreparationManifest, TensorRule
from .conversion import ConvertedTensor, TensorShape
from .converted_store import (
    ConversionReceipt,
    OutputPlan,
    read_conversion_receipt,
)
from .http_transfer import DownloadFailure
from .model_cache import ModelCacheEntry, ModelOnlyCache
from .preparation import PreparationTransfer, TransferProgress
from .registry import (
    CACHE_ROOT_DEFAULT,
    REPOSITORY_ROOT,
    build_inference_manifest,
    load_preparations,
    output_plan_for,
    save_inferences,
    verify_lock_digest,
)
from .runtime import BlockedEvidence
from .serialization_session import ModelInput, OutputWriter, prepare_converted_artifacts
from .source_cache import VerifiedSourceAssets

CHUNK_BYTES = 1024**2
_CHECKPOINT_INTERVAL_BYTES = 16 * 1024**2
_MAX_REDIRECTS = 5
_ALLOWED_HOST_SUFFIXES: dict[Literal["huggingface", "modelscope"], tuple[str, ...]] = {
    "huggingface": ("huggingface.co", ".huggingface.co", ".hf.co"),
    "modelscope": ("modelscope.cn", ".modelscope.cn", ".aliyuncs.com"),
}


def _host_allowed(host: str, mode: Literal["huggingface", "modelscope"]) -> bool:
    normalized = host.rstrip(".").lower()
    if not normalized:
        return False
    for suffix in _ALLOWED_HOST_SUFFIXES[mode]:
        if suffix.startswith("."):
            if normalized.endswith(suffix):
                return True
        elif normalized == suffix:
            return True
    return False


def _source_url(
    manifest: PreparationManifest,
    mode: Literal["huggingface", "modelscope"],
    asset_path: str,
) -> str:
    mirrors = [mirror for mirror in manifest.mirrors if mirror.mode == mode]
    if len(mirrors) != 1:
        raise DownloadFailure("preparation_not_allowlisted")
    mirror = mirrors[0]
    escaped = quote(asset_path, safe="/")
    if mode == "huggingface":
        return f"https://huggingface.co/{mirror.repository}/resolve/{mirror.revision}/{escaped}"
    return f"https://modelscope.cn/models/{mirror.repository}/resolve/{mirror.revision}/{escaped}"


class RedirectingHTTPSStream:
    """Allowlisted HTTPS-only stream following bounded first-party/CDN redirects."""

    def __init__(self, mode: Literal["huggingface", "modelscope"], timeout: float = 60.0) -> None:
        self._mode = mode
        self._timeout = timeout
        self._conn: http.client.HTTPSConnection | None = None
        self._resp: Any = None
        self._closed = False

    def open(
        self,
        url: str,
        offset: int,
        expected_total: int,
        *,
        range_end: int | None = None,
    ) -> tuple[int, int]:
        current_url = url
        ssl_context = ssl.create_default_context()
        if range_end is not None and not offset <= range_end < expected_total:
            raise DownloadFailure("download_range_invalid")
        expected_end = (expected_total - 1) if range_end is None else range_end
        expected_len = expected_end - offset + 1
        use_range = offset > 0 or range_end is not None
        for _ in range(_MAX_REDIRECTS + 1):
            if self._closed:
                raise DownloadFailure("download_response_closed")
            parsed = urlparse(current_url)
            if (
                parsed.scheme != "https"
                or parsed.hostname is None
                or parsed.username is not None
                or parsed.password is not None
                or not _host_allowed(parsed.hostname, self._mode)
            ):
                raise DownloadFailure("download_redirect_unapproved")
            port = parsed.port or 443
            target = parsed.path or "/"
            if parsed.query:
                target = f"{target}?{parsed.query}"
            headers = {
                "Accept-Encoding": "identity",
                "Connection": "close",
                "User-Agent": "Livecho-model-preparation/1",
            }
            if use_range:
                end_spec = "" if range_end is None else str(range_end)
                headers["Range"] = f"bytes={offset}-{end_spec}"
            conn = http.client.HTTPSConnection(
                parsed.hostname,
                port=port,
                timeout=self._timeout,
                context=ssl_context,
            )
            self._conn = conn
            try:
                conn.request("GET", target, headers=headers)
                resp = conn.getresponse()
            except ssl.SSLCertVerificationError:
                self.close()
                raise DownloadFailure("download_tls_rejected") from None
            except (OSError, http.client.HTTPException):
                self.close()
                raise DownloadFailure("download_connection_failed", "transient") from None
            self._resp = resp
            code = resp.status
            if code in {301, 302, 303, 307, 308}:
                location = resp.getheader("Location")
                self._close_conn()
                if not location:
                    raise DownloadFailure("download_redirect_unapproved")
                if location.startswith("/"):
                    location = f"https://{parsed.netloc}{location}"
                current_url = location
                continue
            if code == 401:
                raise DownloadFailure("download_authentication", "authentication")
            if code == 403:
                raise DownloadFailure("download_permission", "permission")
            if code in {408, 500, 502, 503, 504}:
                if resp.getheader("Retry-After") is not None:
                    raise DownloadFailure("download_retry_after_unhandled")
                raise DownloadFailure("download_transient", "transient")
            expected_code = 206 if use_range else 200
            if code != expected_code:
                raise DownloadFailure("download_status_rejected")
            transfer_enc = resp.getheader("Transfer-Encoding")
            content_enc = (resp.getheader("Content-Encoding") or "identity").lower()
            if transfer_enc is not None or content_enc != "identity":
                raise DownloadFailure("download_encoding_rejected")
            raw_len = resp.getheader("Content-Length") or ""
            if not raw_len.isdigit():
                raise DownloadFailure("download_length_invalid")
            length = int(raw_len)
            if length != expected_len:
                raise DownloadFailure("download_length_invalid")
            content_range = resp.getheader("Content-Range")
            if use_range:
                expected_range = f"bytes {offset}-{expected_end}/{expected_total}"
                if content_range != expected_range:
                    raise DownloadFailure("download_range_invalid")
            elif content_range is not None:
                raise DownloadFailure("download_range_invalid")
            return code, length
        raise DownloadFailure("download_redirect_unapproved")

    def read(self, limit: int) -> bytes:
        if self._closed or self._resp is None:
            raise DownloadFailure("download_read_invalid")
        try:
            data = self._resp.read(limit)
        except TimeoutError:
            raise DownloadFailure("transfer_no_progress", "no_progress") from None
        except (OSError, http.client.HTTPException):
            raise DownloadFailure("download_connection_failed", "transient") from None
        if type(data) is not bytes:
            raise DownloadFailure("download_body_invalid")
        return data

    def _close_conn(self) -> None:
        if self._resp is not None:
            with suppress(BaseException):
                self._resp.close()
            self._resp = None
        if self._conn is not None:
            with suppress(BaseException):
                self._conn.close()
            self._conn = None

    def close(self) -> None:
        self._closed = True
        self._close_conn()


def _fetch_range_window(
    mode: Literal["huggingface", "modelscope"],
    url: str,
    start: int,
    end: int,
    total: int,
) -> bytes:
    stream = RedirectingHTTPSStream(mode)
    expected = end - start + 1
    parts: list[bytes] = []
    received = 0
    try:
        stream.open(url, start, total, range_end=end)
        while received < expected:
            chunk = stream.read(min(CHUNK_BYTES, expected - received))
            if not chunk:
                raise DownloadFailure("download_body_truncated", "transient")
            parts.append(chunk)
            received += len(chunk)
        if stream.read(1):
            raise DownloadFailure("download_body_excess")
        return b"".join(parts)
    finally:
        stream.close()


def download_preparation_asset(
    manifest: PreparationManifest,
    mode: Literal["huggingface", "modelscope"],
    asset_path: str,
    cache: ModelOnlyCache,
    *,
    stream_factory: Callable[[Literal["huggingface", "modelscope"]], RedirectingHTTPSStream]
    | None = None,
    clock: Callable[[], int] = time.monotonic_ns,
    progress: Callable[[TransferProgress], None] | None = None,
    cancelled: Callable[[], bool] = lambda: False,
) -> TransferProgress:
    """Download/resume and SHA-256-verify a single asset into ModelOnlyCache."""
    cache.require_preparation(manifest, mode)
    transfer = PreparationTransfer(manifest, mode, asset_path, clock())
    url = _source_url(manifest, mode, asset_path)
    if cancelled():
        raise BlockedEvidence("cancelled")
    entry: ModelCacheEntry = cache.entry(transfer.identity)
    factory = stream_factory or (lambda m: RedirectingHTTPSStream(m))
    try:
        try:
            reader = VerifiedModelReader.from_entry(entry, cancelled, owns_entry=False)
        except MissingModelAsset:
            pass
        else:
            try:
                transfer.received = reader.size
                return transfer.progress("verified")
            finally:
                reader.close()

        offset = entry.offset()
        checkpoint = entry.checkpoint_if_present()
        if checkpoint is None:
            if offset:
                raise BlockedEvidence("checkpoint_missing")
            entry.save_checkpoint(transfer.checkpoint())
        else:
            transfer.restore_checkpoint(checkpoint, clock())

        while True:
            if cancelled():
                raise BlockedEvidence("cancelled")
            if transfer.retry_at_ns is not None:
                delay = max(0.0, (transfer.retry_at_ns - clock()) / 1_000_000_000)
                if delay > 0:
                    time.sleep(delay)
                transfer.resume(transfer.identity, clock())
                entry.save_checkpoint(transfer.checkpoint())
            if transfer.received == transfer.asset.size:
                return transfer.promote(entry, clock())

            if stream_factory is None and transfer.asset.size - transfer.received >= 32 * 1024**2:
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                        while transfer.received < transfer.asset.size:
                            if cancelled():
                                raise BlockedEvidence("cancelled")
                            ranges: list[tuple[int, int]] = []
                            cursor = transfer.received
                            for _ in range(4):
                                if cursor >= transfer.asset.size:
                                    break
                                r_end = min(transfer.asset.size - 1, cursor + 4 * CHUNK_BYTES - 1)
                                ranges.append((cursor, r_end))
                                cursor = r_end + 1
                            futures = [
                                pool.submit(
                                    _fetch_range_window,
                                    mode,
                                    url,
                                    r_start,
                                    r_end,
                                    transfer.asset.size,
                                )
                                for r_start, r_end in ranges
                            ]
                            for future in futures:
                                block = future.result()
                                for pos in range(0, len(block), CHUNK_BYTES):
                                    if cancelled():
                                        raise BlockedEvidence("cancelled")
                                    sub = block[pos : pos + CHUNK_BYTES]
                                    entry.append_model_chunk(sub, transfer.received)
                                    item = transfer.advance(entry.offset(), clock())
                                    if progress is not None:
                                        progress(item)
                            entry.save_checkpoint(transfer.checkpoint())
                except DownloadFailure as error:
                    item = transfer.failure(error.kind, clock())
                    if progress is not None:
                        progress(item)
                    if transfer.stopped:
                        raise
            else:
                stream = factory(mode)
                since_checkpoint = 0
                try:
                    stream.open(url, transfer.received, transfer.asset.size)
                    while transfer.received < transfer.asset.size:
                        if cancelled():
                            raise BlockedEvidence("cancelled")
                        limit = min(CHUNK_BYTES, transfer.asset.size - transfer.received)
                        chunk = stream.read(limit)
                        if type(chunk) is not bytes or len(chunk) > limit:
                            raise DownloadFailure("download_body_invalid")
                        if not chunk:
                            raise DownloadFailure("download_body_truncated", "transient")
                        entry.append_model_chunk(chunk, transfer.received)
                        since_checkpoint += len(chunk)
                        item = transfer.advance(entry.offset(), clock())
                        if (
                            since_checkpoint >= _CHECKPOINT_INTERVAL_BYTES
                            or transfer.received == transfer.asset.size
                        ):
                            entry.save_checkpoint(transfer.checkpoint())
                            since_checkpoint = 0
                        if progress is not None:
                            progress(item)
                    extra = stream.read(1)
                    if extra:
                        raise DownloadFailure("download_body_excess")
                except DownloadFailure as error:
                    if since_checkpoint > 0:
                        with suppress(BaseException):
                            entry.save_checkpoint(transfer.checkpoint())
                    item = transfer.failure(error.kind, clock())
                    if progress is not None:
                        progress(item)
                    if transfer.stopped:
                        raise
                finally:
                    stream.close()

            if transfer.retry_at_ns is None:
                return transfer.promote(entry, clock())
    except BlockedEvidence:
        raise
    except Exception:
        with suppress(BaseException):
            entry.invalidate_partial(transfer.identity)
        raise BlockedEvidence("download_failed") from None
    finally:
        entry.close()


def download_preparation_sources(
    manifest: PreparationManifest,
    mode: Literal["huggingface", "modelscope"],
    cache: ModelOnlyCache,
    *,
    stream_factory: Callable[[Literal["huggingface", "modelscope"]], RedirectingHTTPSStream]
    | None = None,
    progress: Callable[[TransferProgress], None] | None = None,
    cancelled: Callable[[], bool] = lambda: False,
) -> None:
    """Acquire only missing preparation assets into cache."""
    owner = VerifiedSourceAssets(manifest, mode, cache, cancelled)
    try:
        missing = owner.missing_assets()
    finally:
        owner.close()
    for asset in missing:
        download_preparation_asset(
            manifest,
            mode,
            asset.path,
            cache,
            stream_factory=stream_factory,
            progress=progress,
            cancelled=cancelled,
        )


def _import_mlx() -> Any:
    import mlx.core as mx

    return mx


class MLXConversionBackend:
    """PreparationConversionBackend executing real affine 8-bit group-64 quantization in MLX."""

    def __init__(
        self,
        *,
        converter_revision: str,
        dependency_lock_sha256: str,
    ) -> None:
        self.converter_revision = converter_revision
        self.dependency_lock_sha256 = dependency_lock_sha256
        self._unloaded = True
        self._tensors: dict[str, Any] = {}
        self._rules: dict[str, TensorRule] = {}
        self._mx: Any | None = None

    @property
    def unloaded(self) -> bool:
        return self._unloaded

    def load_sources(
        self,
        manifest: PreparationManifest,
        assets: Mapping[str, VerifiedModelReader],
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> tuple[tuple[str, Any], ...]:
        if local_files_only is not True or trust_remote_code is not False:
            raise BlockedEvidence("conversion_admission_failed")
        mx = _import_mlx()
        self._mx = mx
        self._rules = {rule.name: rule for rule in manifest.tensor_map}
        loaded: dict[str, Any] = {}
        weight_paths = sorted(
            asset.path for asset in manifest.source_assets if asset.kind == "weights"
        )
        for path in weight_paths:
            reader = assets.get(path)
            if reader is None:
                raise BlockedEvidence("source_assets_unverified")
            raw = reader.read_all_verified()
            buf = io.BytesIO(raw)
            del raw
            try:
                shard = mx.load(buf, format="safetensors")
            finally:
                buf.close()
            for name, tensor in shard.items():
                if name in loaded:
                    raise BlockedEvidence("tensor_inventory_mismatch")
                loaded[name] = tensor
        if set(loaded) != set(self._rules):
            raise BlockedEvidence("tensor_inventory_mismatch")
        values = list(loaded.values())
        for start in range(0, len(values), 64):
            mx.eval(*values[start : start + 64])
        mx.synchronize()
        self._tensors = loaded
        self._unloaded = False
        return tuple((rule.name, loaded[rule.name]) for rule in manifest.tensor_map)

    def describe(self, name: str, tensor: Any) -> TensorShape:
        rule = self._rules.get(name)
        if rule is None:
            raise BlockedEvidence("tensor_inventory_mismatch")
        return TensorShape(rule=rule, shape=tuple(int(dim) for dim in tensor.shape))

    def quantize(
        self,
        tensor: Any,
        *,
        group_size: int,
        bits: int,
        mode: str,
    ) -> tuple[Any, Any, Any]:
        mx = self._mx or _import_mlx()
        weight, scales, biases = mx.quantize(tensor, group_size=group_size, bits=bits, mode=mode)
        return weight, scales, biases

    def evaluate(self, tensors: tuple[Any, ...]) -> None:
        mx = self._mx or _import_mlx()
        for start in range(0, len(tensors), 64):
            mx.eval(*tensors[start : start + 64])

    def synchronize(self) -> None:
        mx = self._mx or _import_mlx()
        mx.synchronize()

    def close(self) -> None:
        self._tensors.clear()
        self._rules.clear()
        self._unloaded = True
        if self._mx is not None:
            with suppress(BaseException):
                self._mx.clear_cache()


class MLXPreparationSerializer:
    """PreparationSerializer emitting native MLX safetensors + copied non-weight metadata."""

    def __init__(
        self,
        *,
        converter_revision: str,
        dependency_lock_sha256: str,
    ) -> None:
        self.converter_revision = converter_revision
        self.dependency_lock_sha256 = dependency_lock_sha256
        self._fresh = True

    @property
    def fresh(self) -> bool:
        return self._fresh

    def serialize(
        self,
        preparation: PreparationManifest,
        plan: OutputPlan,
        converted: Mapping[str, ConvertedTensor[Any]],
        auxiliary: Mapping[str, ModelInput],
        outputs: OutputWriter,
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> None:
        if local_files_only is not True or trust_remote_code is not False:
            raise BlockedEvidence("serialization_admission_failed")
        mx = _import_mlx()
        out_tensors: dict[str, Any] = {}
        for rule in preparation.tensor_map:
            item = converted[rule.name]
            if rule.operation == "affine-8bit-group64":
                if item.scales is None or item.biases is None:
                    raise BlockedEvidence("serialization_failed")
                prefix = (
                    rule.name.removesuffix(".weight")
                    if rule.name.endswith(".weight")
                    else rule.name
                )
                out_tensors[rule.name] = item.weight
                out_tensors[f"{prefix}.scales"] = item.scales
                out_tensors[f"{prefix}.biases"] = item.biases
            else:
                tensor = item.weight
                if rule.name.startswith("thinker.audio_tower.conv2d") and rule.name.endswith(
                    ".weight"
                ):
                    tensor = mx.transpose(tensor, (0, 2, 3, 1))
                out_tensors[rule.name] = tensor
        values = list(out_tensors.values())
        for start in range(0, len(values), 64):
            mx.eval(*values[start : start + 64])
        mx.synchronize()
        buf = io.BytesIO()
        try:
            mx.save_safetensors(
                buf,
                out_tensors,
                metadata={"format": "mlx", "quantization": "affine-8bit-group64"},
            )
            out_tensors.clear()
            raw = buf.getbuffer()

            def _iter_chunks() -> Iterator[bytes]:
                for offset in range(0, len(raw), CHUNK_BYTES):
                    yield bytes(raw[offset : offset + CHUNK_BYTES])

            outputs.write_output("model.safetensors", _iter_chunks())
            raw.release()
        finally:
            out_tensors.clear()
            buf.close()
            with suppress(BaseException):
                mx.clear_cache()

        for spec in plan.outputs:
            if spec.path == "model.safetensors":
                continue
            aux = auxiliary.get(spec.path)
            if aux is None:
                raise BlockedEvidence("serialization_failed")
            outputs.write_output(spec.path, _iter_model_input(aux))
        self._fresh = False

    def close(self) -> None:
        pass


def _iter_model_input(reader: ModelInput) -> Iterator[bytes]:
    offset = 0
    while offset < reader.size:
        count = min(CHUNK_BYTES, reader.size - offset)
        yield reader.read_at(offset, count)
        offset += count


def prepare_models_for_manifest(
    manifest_id: str,
    mode: Literal["huggingface", "modelscope"],
    *,
    cache_root: Path = CACHE_ROOT_DEFAULT,
    repository_root: Path = REPOSITORY_ROOT,
    progress: Callable[[TransferProgress], None] | None = None,
    cancelled: Callable[[], bool] = lambda: False,
) -> tuple[InferenceManifest, ...]:
    """Acquire verified sources, convert 8-bit group-64, and write inference manifests."""
    verify_lock_digest(repository_root)
    preparations = load_preparations(manifest_id)
    cache_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    sources_root = cache_root / "sources"
    converted_root = cache_root / "converted"
    sources_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    converted_root.mkdir(mode=0o700, parents=True, exist_ok=True)

    inferences_by_model: dict[str, InferenceManifest] = {}
    # Prepare 0.6B first for faster early validation, returning (1.7B, 0.6B) order.
    for preparation in (preparations[1], preparations[0]):
        plan = output_plan_for(preparation)
        receipt: ConversionReceipt | None = None
        with suppress(BlockedEvidence):
            receipt = read_conversion_receipt(
                converted_root,
                repository_root,
                preparation,
                plan,
                cancelled=cancelled,
            )
        if receipt is None:
            with ModelOnlyCache(sources_root, repository_root, preparation, mode) as cache:
                download_preparation_sources(
                    preparation,
                    mode,
                    cache,
                    progress=progress,
                    cancelled=cancelled,
                )
                converter = MLXConversionBackend(
                    converter_revision=preparation.converter_revision,
                    dependency_lock_sha256=preparation.dependency_lock_sha256,
                )
                serializer = MLXPreparationSerializer(
                    converter_revision=preparation.converter_revision,
                    dependency_lock_sha256=preparation.dependency_lock_sha256,
                )
                receipt = asyncio.run(
                    prepare_converted_artifacts(
                        preparation,
                        mode,
                        cache,
                        converter,
                        serializer,
                        plan,
                        converted_root,
                        repository_root,
                        cancelled=cancelled,
                    )
                )
        inferences_by_model[preparation.model] = build_inference_manifest(
            preparation, receipt.outputs
        )

    result = (
        inferences_by_model[preparations[0].model],
        inferences_by_model[preparations[1].model],
    )
    save_inferences(manifest_id, result)
    return result
