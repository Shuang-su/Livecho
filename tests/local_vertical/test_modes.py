"""Mode-gate tests: the closed synthetic_mlx path never starts fixtures."""

from __future__ import annotations

import asyncio

from livecho_backend.local_vertical.config import (
    VIEWER_ENDPOINT_PATH,
    WORKER_ENDPOINT_PATH,
    LocalVerticalConfig,
    LocalVerticalMode,
)
from livecho_backend.local_vertical.schedule import FixtureScheduleSpec
from livecho_backend.local_vertical.service import (
    LocalVerticalService,
    ModeBlockedError,
    create_local_vertical_app,
)
from starlette.routing import Route, WebSocketRoute


def test_synthetic_mlx_selection_is_blocked_with_payload_free_diagnostics() -> None:
    config = LocalVerticalConfig(mode=LocalVerticalMode.SYNTHETIC_MLX, port=0)
    service = LocalVerticalService(config)
    blocked = service.blocked_evidence()
    assert blocked["outcome"] == "blocked_evidence"
    assert blocked["mode"] == "synthetic_mlx"
    assert blocked["real_asr_evidence"] is False
    try:
        asyncio.run(service.start_fixture_session(FixtureScheduleSpec(segments=1)))
    except ModeBlockedError as error:
        assert "synthetic_mlx" in str(error)
    else:
        raise AssertionError("synthetic_mlx must stay closed")


def test_blocked_mlx_request_never_starts_a_fixture_session() -> None:
    async def scenario() -> None:
        config = LocalVerticalConfig(mode=LocalVerticalMode.SYNTHETIC_MLX, port=0)
        service = LocalVerticalService(config)
        try:
            await service.start_fixture_session(FixtureScheduleSpec(segments=1))
        except ModeBlockedError:
            pass
        else:
            raise AssertionError("a blocked MLX request must not start fixtures")
        assert service.timeline.session_status == "stopped"
        assert service.registry.connection_count() == 0
        assert service.observations.publish_count == 0

    asyncio.run(scenario())


def test_fixture_app_mounts_exactly_the_viewer_endpoint() -> None:
    service = LocalVerticalService(LocalVerticalConfig(port=0))
    app = create_local_vertical_app(service)
    websocket_paths = {route.path for route in app.routes if isinstance(route, WebSocketRoute)}
    http_paths = {route.path for route in app.routes if isinstance(route, Route)}
    assert websocket_paths == {VIEWER_ENDPOINT_PATH}
    assert WORKER_ENDPOINT_PATH not in websocket_paths
    # Health is allowed; no public HTTP start/stop/enable control route.
    assert "/health" in http_paths
    assert "/api/control/start" not in http_paths
