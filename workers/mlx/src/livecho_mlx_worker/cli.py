"""Operator CLI: enroll, doctor, benchmark, run. No automatic import-time execution."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path
from typing import Never

from . import __version__
from .config import EnrollRequest, default_config_path, load_config, save_config
from .diagnostics import result, write_json
from .gates import blocked_reasons, capability_notices, evidence_blockers, real_run_allowed


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(2, "livecho-mlx-worker: invalid_arguments\n")


def _parser() -> SafeParser:
    parser = SafeParser(prog="livecho-mlx-worker")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="action", required=True)

    enroll = sub.add_parser("enroll", help="Write closed local worker configuration")
    enroll.add_argument("--config", type=Path, default=None)
    enroll.add_argument("--endpoint-id", default="loopback-local-v1")
    enroll.add_argument("--worker-id", required=True)
    enroll.add_argument("--manifest-id", required=True)
    enroll.add_argument("--host-evidence-id", required=True)

    doctor = sub.add_parser("doctor", help="Diagnose install and evidence gates")
    doctor.add_argument("--config", type=Path, default=None)

    benchmark = sub.add_parser("benchmark", help="Link to Issue #5 blocked benchmark CLI")
    benchmark.add_argument("--config", type=Path, default=None)
    benchmark.add_argument("--manifest", default="demo-manifest")

    run = sub.add_parser("run", help="Gated real/fixture run (execution registry required)")
    run.add_argument("--config", type=Path, default=None)

    return parser


def _config_path(args: argparse.Namespace) -> Path:
    return args.config if getattr(args, "config", None) is not None else default_config_path()


def cmd_enroll(args: argparse.Namespace) -> int:
    path = _config_path(args)
    try:
        config = EnrollRequest(
            endpoint_id=args.endpoint_id,
            worker_id=args.worker_id,
            manifest_id=args.manifest_id,
            host_evidence_id=args.host_evidence_id,
        ).to_config()
    except Exception:
        sys.stdout.write(
            write_json(
                result(
                    action="enroll",
                    state="invalid_configuration",
                    reasons=("invalid_configuration",),
                )
            )
        )
        return 2
    save_config(path, config)
    sys.stdout.write(
        write_json(
            result(
                action="enroll",
                state="ok",
                extra={"config_name": path.name, "endpoint_id": config.endpoint_id},
            )
        )
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    path = _config_path(args)
    reasons: list[str] = []
    config_ok = False
    if path.is_file():
        try:
            load_config(path)
            config_ok = True
        except Exception:
            reasons.append("invalid_configuration")
    else:
        reasons.append("invalid_configuration")

    reasons.extend(evidence_blockers(require_execution=False))
    reasons.extend(capability_notices())

    # Non-Apple Silicon cannot run real MLX; doctor reports this without probing MLX.
    if platform.system() != "Darwin" or "arm" not in platform.machine().lower():
        reasons.append("non_apple_silicon_mlx")

    if "invalid_configuration" in reasons:
        state = "invalid_configuration"
    elif evidence_blockers(require_execution=False) or "non_apple_silicon_mlx" in reasons:
        state = "blocked_evidence"
    else:
        state = "ok"
    code = 0 if state == "ok" else 2
    sys.stdout.write(
        write_json(
            result(
                action="doctor",
                state=state,
                reasons=tuple(dict.fromkeys(reasons)),  # type: ignore[arg-type]
                extra={
                    "config_present": config_ok,
                    "platform": platform.system(),
                    "machine": platform.machine(),
                    "execution_registry_open": real_run_allowed(),
                },
            )
        )
    )
    return code


def cmd_benchmark(args: argparse.Namespace) -> int:
    reasons = list(blocked_reasons(require_execution=False))
    # Optionally invoke the Issue #5 blocked CLI; never treat its block as a pass.
    asr = [
        sys.executable,
        "-m",
        "tools.asr_benchmark",
        "preflight",
        "--manifest",
        args.manifest,
    ]
    try:
        completed = subprocess.run(
            asr,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(Path.cwd()),
        )
        asr_exit = completed.returncode
        asr_blocked = asr_exit == 2 and "blocked_evidence" in (completed.stdout or "")
    except (OSError, subprocess.SubprocessError):
        asr_exit = -1
        asr_blocked = False
        reasons.append("benchmark_report_unavailable")

    sys.stdout.write(
        write_json(
            result(
                action="benchmark",
                state="blocked_evidence",
                reasons=tuple(reasons),
                extra={
                    "asr_benchmark_exit": asr_exit,
                    "asr_benchmark_blocked": asr_blocked,
                    "selects_model": False,
                },
            )
        )
    )
    return 2


def cmd_run(args: argparse.Namespace) -> int:
    path = _config_path(args)
    reasons = list(blocked_reasons(require_execution=True))
    if not path.is_file():
        reasons.insert(0, "invalid_configuration")
    else:
        try:
            load_config(path)
        except Exception:
            reasons.insert(0, "invalid_configuration")

    # Real path stays closed. Fixture protocol coverage lives in tests/worker, not here.
    sys.stdout.write(
        write_json(
            result(
                action="run",
                state="blocked_evidence",
                reasons=tuple(dict.fromkeys(reasons)),
                extra={
                    "opens_lease": False,
                    "loads_mlx": False,
                    "downloads": False,
                },
            )
        )
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.action == "enroll":
        return cmd_enroll(args)
    if args.action == "doctor":
        return cmd_doctor(args)
    if args.action == "benchmark":
        return cmd_benchmark(args)
    if args.action == "run":
        return cmd_run(args)
    parser.error("action")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
