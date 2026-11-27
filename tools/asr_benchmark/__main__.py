"""Manual local entry points bound strictly to reviewed local manifest identifiers."""

import argparse
import json
import re
import sys
from typing import Never

from .registry import require_reviewed_id
from .runtime import BlockedEvidence


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # argparse's default echoes arbitrary arguments (potential paths/credentials).
        self.exit(2, "asr-benchmark: invalid_arguments\n")


def _blocked_response(action: str, reason: str) -> dict[str, object]:
    if reason == "reviewed_manifest_unavailable":
        reasons = [
            "reviewed_manifest_unavailable",
            "independent_mlx_adapter_unavailable",
            "approved_corpus_unavailable",
            "protected_host_evidence_unavailable",
        ]
    else:
        reasons = [reason]
    return {
        "schema_version": 1,
        "state": "blocked_evidence",
        "action": action,
        "reasons": reasons,
    }


def main(argv: list[str] | None = None) -> int:
    parser = SafeParser(prog="asr-benchmark")
    parser.add_argument("action", choices=("prepare-models", "preflight", "run"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source", choices=("huggingface", "modelscope"))
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}", args.manifest):
        parser.error("manifest")
    if (args.action == "prepare-models") != (args.source is not None):
        parser.error("source")

    try:
        # Fails closed before touching any filesystem path or network socket.
        require_reviewed_id(args.manifest)
        if args.action == "prepare-models":
            from .mlx_converter import prepare_models_for_manifest

            inferences = prepare_models_for_manifest(args.manifest, args.source)
            payload: dict[str, object] = {
                "schema_version": 1,
                "state": "prepared",
                "action": args.action,
                "manifest_id": args.manifest,
                "source": args.source,
                "models": [item.model for item in inferences],
            }
            sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
            return 0
        if args.action == "preflight":
            from .mlx_runner import run_preflight

            payload = run_preflight(args.manifest)
            sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
            return 0

        from .mlx_runner import run_benchmark_matrix
        from .report import cold_populations

        report, decision, report_path = run_benchmark_matrix(args.manifest)
        payload = {
            "schema_version": 1,
            "state": decision.state,
            "action": args.action,
            "manifest_id": args.manifest,
            "run_id": report.run_id,
            "report_path": str(report_path.relative_to(report_path.parents[3])),
            "repetitions": len(report.repetitions),
            "missing": list(decision.missing),
            "failed_1_7b": list(decision.failed_1_7b),
            "failed_0_6b": list(decision.failed_0_6b),
            "cold_populations": cold_populations(report),
        }
        sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
        return 0
    except BlockedEvidence as exc:
        sys.stdout.write(
            json.dumps(_blocked_response(args.action, str(exc)), sort_keys=True) + "\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
