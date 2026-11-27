"""Local WSS helpers. All disposable key material stays in memory."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import os
import socket
import ssl
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from websockets.asyncio.client import ClientConnection, connect
from websockets.datastructures import Headers, HeadersLike
from websockets.typing import Subprotocol

from tests.worker_identity.support import World, b64, b64decode, fresh_key

GATEWAY_PATH = "/api/worker/ws"
GATEWAY_PROTOCOL = Subprotocol("livecho.worker.v1")


@dataclass(frozen=True, slots=True, repr=False)
class Device:
    id: str
    key: Ed25519PrivateKey

    def challenge(self, world: World, client_ip: str = "127.0.0.1") -> Challenge:
        reply = world.service.issue_challenge(self.id, b"{}", client_ip)
        assert reply.status == 201
        assert isinstance(reply.payload, dict)
        challenge_id = reply.payload["challenge_id"]
        nonce = reply.payload["nonce"]
        assert isinstance(challenge_id, str) and isinstance(nonce, str)
        return Challenge(self, challenge_id, b64decode(nonce))


@dataclass(frozen=True, slots=True, repr=False)
class Challenge:
    device: Device
    id: str
    nonce: bytes

    def headers(self, key: bytes) -> list[tuple[bytes, bytes]]:
        device_id = self.device.id.encode("ascii")
        challenge_id = self.id.encode("ascii")
        signed = (
            b"livecho-worker-gateway-upgrade-v1\x00"
            + device_id
            + b"\x00"
            + challenge_id
            + b"\x00"
            + self.nonce
            + key
        )
        return [
            (b"livecho-device-id", device_id),
            (b"livecho-challenge-id", challenge_id),
            (b"livecho-device-signature", b64(self.device.key.sign(signed)).encode("ascii")),
            (b"sec-websocket-key", base64.b64encode(key)),
        ]


def enroll(world: World) -> Device:
    private, public = fresh_key()
    issued = world.issue()
    assert issued.status == 201
    registered = world.enroll(issued.json()["token"], public)
    assert registered.status == 201
    device_id = registered.json()["device_id"]
    assert isinstance(device_id, str)
    return Device(device_id, private)


@contextmanager
def _pipe_path(data: bytes) -> Iterator[str]:
    read_fd, write_fd = os.pipe()
    try:
        with os.fdopen(write_fd, "wb") as sink:
            sink.write(data)
        yield f"/dev/fd/{read_fd}"
    finally:
        os.close(read_fd)


def _tls_contexts() -> tuple[ssl.SSLContext, ssl.SSLContext]:
    private = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Livecho loopback test")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(minutes=5))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]),
            critical=False,
        )
        .sign(private, hashes.SHA256())
        .public_bytes(serialization.Encoding.PEM)
    )
    key = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    with _pipe_path(certificate) as cert_path, _pipe_path(key) as key_path:
        server.load_cert_chain(cert_path, key_path)
    client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    client.load_verify_locations(cadata=certificate.decode("ascii"))
    return server, client


@asynccontextmanager
async def serve_gateway(app: FastAPI) -> AsyncIterator[tuple[str, ssl.SSLContext]]:
    server_tls, client_tls = _tls_contexts()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        config = uvicorn.Config(
            app,
            lifespan="off",
            ws="websockets-sansio",
            log_level="error",
            proxy_headers=False,
        )
        config.load()
        config.ssl = server_tls
        server = uvicorn.Server(config)
        serving = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            async with asyncio.timeout(5):
                while not server.started:
                    if serving.done():
                        await serving
                        raise RuntimeError("gateway server exited before startup")
                    await asyncio.sleep(0.01)
            yield f"wss://127.0.0.1:{port}{GATEWAY_PATH}", client_tls
        finally:
            server.should_exit = True
            await asyncio.wait_for(serving, timeout=5)


def connect_worker(
    url: str, tls: ssl.SSLContext, challenge: Challenge, *, additional: HeadersLike | None = None
) -> connect:
    class BoundConnection(ClientConnection):
        async def handshake(
            self,
            additional_headers: HeadersLike | None = None,
            user_agent_header: str | None = None,
        ) -> None:
            key = base64.b64decode(self.protocol.key, validate=True)
            headers = Headers(
                [
                    (name.decode("ascii"), value.decode("ascii"))
                    for name, value in challenge.headers(key)
                    if name != b"sec-websocket-key"
                ]
            )
            if additional_headers is not None:
                headers.update(additional_headers)
            await super().handshake(headers, user_agent_header)

    return connect(
        url,
        subprotocols=[GATEWAY_PROTOCOL],
        proxy=None,
        ssl=tls,
        open_timeout=3,
        close_timeout=2,
        additional_headers=additional,
        create_connection=BoundConnection,
    )
