"""Restricted first-party HTTPS transport, with no installed execution registry.

Only immutable model requests can be built. Redirects, credentials, compression,
chunked framing and unknown lengths are deliberately unsupported. No server text is
returned in diagnostics. ModelScope endpoint authority remains unestablished.
"""

import asyncio
import re
import ssl
from typing import Literal, Protocol
from urllib.parse import quote

from pydantic import model_validator

from .contracts import Asset, Closed, Model, Nonnegative, PreparationManifest, Revision
from .runtime import BlockedEvidence

HEADER_LIMIT = 16_384
CHUNK_LIMIT = 65_536
HOST = "huggingface.co"
FailureKind = Literal["transient", "no_progress", "authentication", "permission", "integrity"]


class DownloadFailure(BlockedEvidence):
    def __init__(self, reason: str, kind: FailureKind = "integrity") -> None:
        super().__init__(reason)
        self.kind = kind


class ModelRequest(Closed):
    repository: Model
    revision: Revision
    asset: Asset
    offset: Nonnegative

    @model_validator(mode="after")
    def bounded(self) -> "ModelRequest":
        if self.offset >= self.asset.size:
            raise ValueError("request_offset")
        if any(ord(char) < 32 or ord(char) == 127 for char in self.asset.path):
            raise ValueError("request_path")
        return self

    def wire(self) -> bytes:
        # Every path segment is escaped; no asset string becomes a header or authority.
        path = quote(self.asset.path, safe="/")
        target = f"/{self.repository}/resolve/{self.revision}/{path}"
        resume = f"Range: bytes={self.offset}-\r\n" if self.offset else ""
        return (
            f"GET {target} HTTP/1.1\r\nHost: {HOST}\r\n"
            "Accept-Encoding: identity\r\nConnection: close\r\n"
            f"User-Agent: Livecho-model-preparation/1\r\n{resume}\r\n"
        ).encode("ascii")


def model_request(
    manifest: PreparationManifest,
    mode: Literal["huggingface", "modelscope"],
    asset_path: str,
    offset: int,
) -> ModelRequest:
    if mode != "huggingface":
        raise DownloadFailure("download_endpoint_unverified")
    mirrors = [m for m in manifest.mirrors if m.mode == mode]
    assets = [a for a in manifest.source_assets if a.path == asset_path]
    if len(mirrors) != 1 or len(assets) != 1:
        raise DownloadFailure("preparation_not_allowlisted")
    try:
        return ModelRequest(
            repository=mirrors[0].repository,
            revision=mirrors[0].revision,
            asset=assets[0],
            offset=offset,
        )
    except ValueError:
        raise DownloadFailure("download_request_invalid") from None


def validate_response(header: bytes, request: ModelRequest) -> None:
    """Accept only one exact-length, identity-encoded response for this requested suffix."""
    if type(header) is not bytes or len(header) > HEADER_LIMIT or not header.endswith(b"\r\n\r\n"):
        raise DownloadFailure("download_headers_invalid")
    lines = header[:-4].split(b"\r\n")
    if len(lines) > 100 or any(len(line) > 8192 for line in lines):
        raise DownloadFailure("download_headers_invalid")
    status = re.fullmatch(rb"HTTP/1\.[01] ([0-9]{3})[ \t][\x20-\x7e\t]*", lines[0])
    if status is None:
        raise DownloadFailure("download_headers_invalid")
    fields: dict[bytes, bytes] = {}
    for line in lines[1:]:
        name, separator, value = line.partition(b":")
        if (
            not separator
            or re.fullmatch(rb"[!#$%&'*+.^_`|~0-9a-zA-Z-]+", name) is None
            or re.fullmatch(rb"[\x20-\x7e\t]*", value) is None
            or name.lower() in fields
        ):
            raise DownloadFailure("download_headers_invalid")
        fields[name.lower()] = value.strip(b" \t")
    code = int(status[1])
    if code == 401:
        raise DownloadFailure("download_authentication", "authentication")
    if code == 403:
        raise DownloadFailure("download_permission", "permission")
    if code in {408, 500, 502, 503, 504}:
        # Fixed 1/2-second retries cannot honor an arbitrary server cooldown. Stop,
        # including malformed/date values, instead of silently ignoring Retry-After.
        if b"retry-after" in fields:
            raise DownloadFailure("download_retry_after_unhandled")
        raise DownloadFailure("download_transient", "transient")
    if 300 <= code < 400:
        raise DownloadFailure("download_redirect_unapproved")
    # 429 is terminal: the fixed retry schedule must not evade an operator's rate limit.
    if code != (206 if request.offset else 200):
        raise DownloadFailure("download_status_rejected")
    if (
        b"transfer-encoding" in fields
        or fields.get(b"content-encoding", b"identity") != b"identity"
    ):
        raise DownloadFailure("download_encoding_rejected")
    length = fields.get(b"content-length", b"")
    if re.fullmatch(rb"[0-9]{1,20}", length) is None:
        raise DownloadFailure("download_length_invalid")
    if int(length) != request.asset.size - request.offset:
        raise DownloadFailure("download_length_invalid")
    content_range = fields.get(b"content-range")
    if request.offset:
        expected = f"bytes {request.offset}-{request.asset.size - 1}/{request.asset.size}".encode()
        if content_range != expected:
            raise DownloadFailure("download_range_invalid")
    elif content_range is not None:
        raise DownloadFailure("download_range_invalid")


class ModelResponse(Protocol):
    """A single attempt. close must synchronously revoke IO, including after cancellation."""

    async def start(self, request: ModelRequest) -> bytes: ...

    async def read(self, limit: int) -> bytes: ...

    def close(self) -> None: ...


class HTTPSResponse:
    """TLS verification on, fixed authority, no environment proxy/token/URL integration."""

    def __init__(self) -> None:
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._started = self._closed = False

    async def start(self, request: ModelRequest) -> bytes:
        if self._started or self._closed:
            raise DownloadFailure("download_response_closed")
        self._started = True
        # Revalidate even a model_construct/model_copy caller before emitting a request.
        request = ModelRequest.model_validate(request.model_dump())
        try:
            reader, writer = await asyncio.open_connection(
                HOST,
                443,
                ssl=ssl.create_default_context(),
                server_hostname=HOST,
                limit=HEADER_LIMIT,
                ssl_handshake_timeout=60,
                ssl_shutdown_timeout=1,
            )
            self._reader, self._writer = reader, writer
            if self._closed:
                self.close()
                raise DownloadFailure("download_response_closed")
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                raise asyncio.CancelledError
            writer.write(request.wire())
            await writer.drain()
            if task is not None and task.cancelling():
                raise asyncio.CancelledError
            return await reader.readuntil(b"\r\n\r\n")
        except ssl.SSLCertVerificationError:
            raise DownloadFailure("download_tls_rejected") from None
        except asyncio.LimitOverrunError:
            raise DownloadFailure("download_headers_invalid") from None
        except (OSError, EOFError):
            raise DownloadFailure("download_connection_failed", "transient") from None

    async def read(self, limit: int) -> bytes:
        if (
            self._closed
            or self._reader is None
            or type(limit) is not int
            or not 0 < limit <= CHUNK_LIMIT
        ):
            raise DownloadFailure("download_read_invalid")
        try:
            return await self._reader.read(limit)
        except OSError:
            raise DownloadFailure("download_connection_failed", "transient") from None

    def close(self) -> None:
        self._closed = True
        if self._writer is not None:
            # Abort has no awaited TLS shutdown that a second cancellation could interrupt.
            self._writer.transport.abort()
        self._reader = None
