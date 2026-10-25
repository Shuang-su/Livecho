"""Original HTTP metadata and transport doubles; no sockets, models or audio."""

import asyncio
import ssl
from typing import Any

import pytest

from tools.asr_benchmark.http_transfer import (
    CHUNK_LIMIT,
    HEADER_LIMIT,
    HOST,
    DownloadFailure,
    HTTPSResponse,
    ModelRequest,
    model_request,
    validate_response,
)

from .factories import preparation


def request(offset: int = 0) -> ModelRequest:
    return model_request(preparation(), "huggingface", "NOTICE.txt", offset)


def header(status: int = 200, fields: bytes = b"Content-Length: 100\r\n") -> bytes:
    return b"HTTP/1.1 " + str(status).encode() + b" Test\r\n" + fields + b"\r\n"


def test_fixed_request_authority_and_immutable_revision() -> None:
    value = request(15)
    wire = value.wire()
    assert (
        wire
        == (
            f"GET /Qwen/Qwen3-ASR-1.7B/resolve/{value.revision}/NOTICE.txt HTTP/1.1\r\n"
            "Host: huggingface.co\r\nAccept-Encoding: identity\r\nConnection: close\r\n"
            "User-Agent: Livecho-model-preparation/1\r\nRange: bytes=15-\r\n\r\n"
        ).encode()
    )
    assert b"Range:" not in request().wire()
    special = value.model_dump()
    special["asset"]["path"] = "notes/a ?#%中.txt"
    assert b"notes/a%20%3F%23%25%E4%B8%AD.txt" in ModelRequest.model_validate(special).wire()


@pytest.mark.parametrize("offset", [-1, True, 100, 101])
def test_offset_bounds(offset: int) -> None:
    with pytest.raises(DownloadFailure, match="request_invalid"):
        request(offset)


def test_unknown_asset_and_unverified_mirror_are_blocked() -> None:
    with pytest.raises(DownloadFailure, match="not_allowlisted"):
        model_request(preparation(), "huggingface", "other.txt", 0)
    with pytest.raises(DownloadFailure, match="endpoint_unverified"):
        model_request(preparation(), "modelscope", "NOTICE.txt", 0)
    for field, value in (("repository", "other/repo"), ("revision", "main"), ("url", "test")):
        record = request().model_dump()
        record[field] = value
        with pytest.raises(ValueError):
            ModelRequest.model_validate(record)
    record = request().model_dump()
    record["asset"]["path"] = "notice\r\nHost.txt"
    with pytest.raises(ValueError):
        ModelRequest.model_validate(record)


def test_exact_initial_and_suffix_responses() -> None:
    validate_response(header(), request())
    validate_response(
        header(206, b"content-length: 85\r\nContent-Range: bytes 15-99/100\r\n"), request(15)
    )


@pytest.mark.parametrize(
    ("status", "fields", "offset", "reason"),
    [
        (200, b"Content-Length: 100\r\n", 15, "status"),
        (206, b"Content-Length: 100\r\n", 0, "status"),
        (416, b"Content-Range: bytes */100\r\n", 15, "status"),
        (429, b"Retry-After: 600\r\n", 0, "status"),
        (302, b"Location: https://example.invalid/private?token=secret\r\n", 0, "redirect"),
        (200, b"Content-Length: 99\r\n", 0, "length"),
        (200, b"", 0, "length"),
        (200, b"Content-Length: +100\r\n", 0, "length"),
        (200, b"Content-Length: " + b"9" * 100 + b"\r\n", 0, "length"),
        (200, b"Content-Length: 100\r\ncontent-length: 100\r\n", 0, "headers"),
        (200, b" Content-Length: 100\r\n", 0, "headers"),
        (200, b"Content-Length: 100\nX: test\r\n", 0, "headers"),
        (200, b"Content-Length: 100\r\nContent-Encoding: gzip\r\n", 0, "encoding"),
        (200, b"Content-Length: 100\r\nTransfer-Encoding: chunked\r\n", 0, "encoding"),
        (200, b"Content-Length: 100\r\nContent-Range: bytes 0-99/100\r\n", 0, "range"),
        (206, b"Content-Length: 85\r\n", 15, "range"),
        (206, b"Content-Length: 85\r\nContent-Range: bytes 14-98/100\r\n", 15, "range"),
        (206, b"Content-Length: 85\r\nContent-Range: bytes 15-99/*\r\n", 15, "range"),
        (206, b"Content-Length: 85\r\nContent-Range: bytes 15-99/101\r\n", 15, "range"),
    ],
)
def test_response_contract_rejects_ambiguous_or_unsupported_payloads(
    status: int, fields: bytes, offset: int, reason: str
) -> None:
    with pytest.raises(DownloadFailure, match=reason) as caught:
        validate_response(header(status, fields), request(offset))
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("status", [401, 403, 408, 500, 502, 503, 504])
def test_status_failure_classification(status: int) -> None:
    with pytest.raises(DownloadFailure) as caught:
        validate_response(header(status), request())
    assert caught.value.kind == {401: "authentication", 403: "permission"}.get(status, "transient")


@pytest.mark.parametrize("value", [b"120", b"Fri, 03 Oct 2026 18:00:00 GMT", b"invalid", b""])
def test_server_cooldown_is_not_silently_ignored(value: bytes) -> None:
    with pytest.raises(DownloadFailure, match="retry_after_unhandled") as caught:
        validate_response(header(503, b"Retry-After: " + value + b"\r\n"), request())
    assert caught.value.kind == "integrity"


@pytest.mark.parametrize(
    "raw",
    [
        b"HTTP/2 200 Test\r\n\r\n",
        b"incomplete",
        header(fields=b"X: " + b"a" * HEADER_LIMIT + b"\r\n"),
    ],
)
def test_header_limit_and_syntax(raw: bytes) -> None:
    with pytest.raises(DownloadFailure, match="headers"):
        validate_response(raw, request())


class Reader:
    def __init__(self) -> None:
        self.limits: list[int] = []

    async def readuntil(self, separator: bytes) -> bytes:
        assert separator == b"\r\n\r\n"
        return header()

    async def read(self, limit: int) -> bytes:
        self.limits.append(limit)
        return b""


class Writer:
    def __init__(self) -> None:
        self.transport = self
        self.aborted = False
        self.writes: list[bytes] = []

    def write(self, value: bytes) -> None:
        self.writes.append(value)

    async def drain(self) -> None:
        pass

    def abort(self) -> None:
        self.aborted = True


def test_stream_transport_is_fixed_tls_bounded_and_revocable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, writer = Reader(), Writer()

    async def connect(host: str, port: int, **kwargs: Any) -> tuple[Reader, Writer]:
        assert (host, port) == (HOST, 443)
        assert kwargs["server_hostname"] == HOST
        assert kwargs["limit"] == HEADER_LIMIT
        context = kwargs["ssl"]
        assert isinstance(context, ssl.SSLContext)
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        return reader, writer

    monkeypatch.setattr(asyncio, "open_connection", connect)

    async def exercise() -> None:
        response = HTTPSResponse()
        assert await response.start(request()) == header()
        assert writer.writes == [request().wire()]
        assert await response.read(CHUNK_LIMIT) == b""
        with pytest.raises(DownloadFailure):
            await response.read(CHUNK_LIMIT + 1)
        response.close()
        response.close()
        assert writer.aborted
        with pytest.raises(DownloadFailure):
            await response.read(1)
        with pytest.raises(DownloadFailure):
            await response.start(request())

    asyncio.run(exercise())
