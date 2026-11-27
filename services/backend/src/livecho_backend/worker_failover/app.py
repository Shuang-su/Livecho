"""Explicit app factory for the isolated synthetic three-worker exercise."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

from livecho_backend.local_vertical.config import VIEWER_ENDPOINT_PATH
from livecho_backend.worker_gateway.gateway import WORKER_PATH

from .gateway import SyntheticFailoverGateway
from .viewer import loopback_wss


def create_failover_app(gateway: SyntheticFailoverGateway, web_root: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await gateway.stop()

    app = FastAPI(
        title="Livecho synthetic failover",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @app.websocket(WORKER_PATH)
    async def worker(socket: WebSocket) -> None:
        if not loopback_wss(socket):
            await socket.close(code=1008)
            return
        await gateway.serve(socket)

    app.add_api_websocket_route(VIEWER_ENDPOINT_PATH, gateway.viewers.serve)
    if web_root is not None:
        app.mount("/", StaticFiles(directory=web_root, html=True), name="captions")
    return app
