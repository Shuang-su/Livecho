"""One-command local vertical demo runner."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
from pathlib import Path

import uvicorn

from .config import LocalVerticalConfig, LocalVerticalMode
from .demo_client import run_demo_client
from .schedule import FixtureScheduleSpec
from .service import LocalVerticalService, ModeBlockedError, create_local_vertical_app
from .timeline import FixtureScheduleError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Livecho local caption vertical demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--room", default=LocalVerticalConfig().room_id)
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in LocalVerticalMode],
        default=LocalVerticalMode.FIXTURE_TIMELINE.value,
    )
    parser.add_argument("--segments", type=int, default=12)
    parser.add_argument("--interval-ms", type=int, default=3_000)
    parser.add_argument("--no-partials", action="store_true")
    parser.add_argument("--server-only", action="store_true")
    parser.add_argument("--client-only", action="store_true")
    parser.add_argument(
        "--static-root",
        type=Path,
        default=None,
        help="Optional apps/web/dist directory to serve on the same origin",
    )
    parser.add_argument("--stop-at", type=int, default=None)
    parser.add_argument("--stop-reason", default="ingest_disabled")
    parser.add_argument("--fail-at", type=int, default=None)
    parser.add_argument("--delete-at", type=int, default=None)
    parser.add_argument("--disable-at", type=int, default=None)
    parser.add_argument("--close-at", type=int, default=None)
    return parser


def _spec_from_args(args: argparse.Namespace) -> FixtureScheduleSpec:
    return FixtureScheduleSpec(
        segments=max(1, args.segments),
        interval_ms=args.interval_ms,
        with_partials=not args.no_partials,
        stop_after_segment=args.stop_at,
        stop_reason=args.stop_reason if args.stop_at is not None else None,
        fail_after_segment=args.fail_at,
        delete_after_segment=args.delete_at,
        disable_after_segment=args.disable_at,
        close_after_segment=args.close_at,
    )


async def _run_fixture_demo(config: LocalVerticalConfig, spec: FixtureScheduleSpec) -> int:
    service = LocalVerticalService(config)
    app = create_local_vertical_app(service)
    server = uvicorn.Server(
        uvicorn.Config(app, host=config.host, port=config.port, log_level="warning"),
    )
    serve_task = asyncio.create_task(server.serve())
    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.05)
    fast_spec = spec
    if spec.segments <= 4:
        fast_spec = FixtureScheduleSpec(
            segments=spec.segments,
            interval_ms=min(spec.interval_ms, 800),
            with_partials=spec.with_partials,
            stop_after_segment=spec.stop_after_segment,
            stop_reason=spec.stop_reason,
            fail_after_segment=spec.fail_after_segment,
            delete_after_segment=spec.delete_after_segment,
            disable_after_segment=spec.disable_after_segment,
            close_after_segment=spec.close_after_segment,
        )
    await service.start_fixture_session(fast_spec)
    client_result = await run_demo_client(
        host=config.host, port=config.port, room_id=config.room_id
    )
    await server.shutdown()
    serve_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await serve_task
    if client_result.exit_code != 0 or client_result.terminal_status != "stopped":
        print(
            json.dumps(
                {
                    "outcome": "fixture_failed",
                    "terminal_status": client_result.terminal_status,
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "outcome": "fixture_complete",
                "terminal_status": client_result.terminal_status,
                "observations": service.observations.snapshot(),
            }
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode = LocalVerticalMode(args.mode)
    config = LocalVerticalConfig(
        mode=mode,
        host=args.host,
        port=args.port,
        room_id=args.room,
    )
    if mode == LocalVerticalMode.SYNTHETIC_MLX:
        service = LocalVerticalService(config)
        print(json.dumps(service.blocked_evidence()))
        return 2
    if args.client_only:
        result = asyncio.run(
            run_demo_client(host=config.host, port=config.port, room_id=config.room_id)
        )
        return result.exit_code
    spec = _spec_from_args(args)
    if args.server_only:
        service = LocalVerticalService(config)

        async def _serve() -> None:
            app = create_local_vertical_app(service, static_root=args.static_root)
            await service.start_fixture_session(spec)
            server = uvicorn.Server(
                uvicorn.Config(app, host=config.host, port=config.port, log_level="info"),
            )
            await server.serve()

        asyncio.run(_serve())
        return 0
    try:
        return asyncio.run(_run_fixture_demo(config, spec))
    except ModeBlockedError:
        print(json.dumps(LocalVerticalService(config).blocked_evidence()))
        return 2
    except FixtureScheduleError as error:
        print(json.dumps({"outcome": "blocked_evidence", "reason": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
