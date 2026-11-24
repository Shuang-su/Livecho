"""HTTP routes for worker enrollment, device proof, and contribution statistics.

This application is unmounted by default. It does not set an account session
cookie and it does not read the process environment.
"""

from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.responses import Response

from livecho_backend.auth.crypto import session_cookie_value
from livecho_backend.auth.records import Principal

from .records import IP_FALLBACK
from .service import (
    AccountLookup,
    ApiResult,
    Clock,
    NewId,
    PrincipalResolver,
    RandomBytes,
    build_service,
)
from .store import MemoryWorkerIdentityStore

_JSON = "application/json"


def create_worker_identity_app(
    *,
    store: MemoryWorkerIdentityStore | None = None,
    accounts: AccountLookup | None = None,
    principal_for_cookie: PrincipalResolver | None = None,
    enrollment_key: bytes | None = None,
    clock: Clock | None = None,
    random_bytes: RandomBytes | None = None,
    new_id: NewId | None = None,
) -> FastAPI:
    """Build the worker-identity application. A missing key leaves issuance unavailable."""
    service = build_service(
        store=store,
        accounts=accounts,
        enrollment_key=enrollment_key,
        clock=clock,
        random_bytes=random_bytes,
        new_id=new_id,
    )
    app = FastAPI(
        title="Livecho worker identity",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )
    app.state.worker_service = service
    app.state.worker_store = service.store

    def respond(result: ApiResult) -> Response:
        if result.payload is None:
            return Response(status_code=result.status, headers={"cache-control": "no-store"})
        return Response(
            content=json.dumps(result.payload, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            ),
            status_code=result.status,
            media_type=_JSON,
            headers={"cache-control": "no-store"},
        )

    def client_ip(request: Request) -> str:
        if request.client is None or not request.client.host:
            return IP_FALLBACK
        return request.client.host

    def principal_for(request: Request) -> Principal | None:
        if principal_for_cookie is None:
            return None
        return principal_for_cookie(session_cookie_value(request.headers.get("cookie")))

    @app.post("/api/worker/enrollment-tokens")
    async def issue_enrollment(request: Request) -> Response:
        return respond(service.issue_enrollment(principal_for(request), await request.body()))

    @app.post("/api/worker/devices")
    async def enroll_device(request: Request) -> Response:
        return respond(service.enroll_device(await request.body(), client_ip(request)))

    @app.post("/api/worker/devices/{device_id}/challenges")
    async def issue_challenge(device_id: str, request: Request) -> Response:
        return respond(service.issue_challenge(device_id, await request.body(), client_ip(request)))

    @app.post("/api/worker/challenges/{challenge_id}/verify")
    async def verify_challenge(challenge_id: str, request: Request) -> Response:
        return respond(
            service.verify_challenge(challenge_id, await request.body(), client_ip(request))
        )

    @app.post("/api/worker/devices/{device_id}/revoke")
    async def revoke_device(device_id: str, request: Request) -> Response:
        return respond(
            service.revoke_device(principal_for(request), device_id, await request.body())
        )

    @app.post("/api/worker/allowlist")
    async def add_allowlist(request: Request) -> Response:
        return respond(service.add_allowlist(principal_for(request), await request.body()))

    @app.delete("/api/worker/allowlist")
    async def remove_allowlist(request: Request) -> Response:
        return respond(service.remove_allowlist(principal_for(request), await request.body()))

    @app.get("/api/worker/allowlist")
    async def list_allowlist(request: Request) -> Response:
        return respond(service.list_allowlist(principal_for(request)))

    @app.get("/api/worker/statistics")
    async def read_statistics(request: Request) -> Response:
        return respond(service.read_statistics(principal_for(request), request.url.query))

    @app.get("/api/worker/devices")
    async def list_devices(request: Request) -> Response:
        return respond(service.list_devices(principal_for(request), request.url.query))

    return app
