"""Manual local entry points. No manifest/provider has been approved for execution."""

import argparse
import json
import re
import sys
from typing import Never


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # argparse's default echoes arbitrary arguments (potential paths/credentials).
        self.exit(2, "asr-benchmark: invalid_arguments\n")


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
    # Deliberately empty reviewed execution registry. Input is an identifier, never
    # a path, import name, URL, command, loader option or server-provided manifest.
    result = {
        "schema_version": 1,
        "state": "blocked_evidence",
        "action": args.action,
        "reasons": [
            "reviewed_manifest_unavailable",
            "independent_mlx_adapter_unavailable",
            "approved_corpus_unavailable",
            "protected_host_evidence_unavailable",
        ],
    }
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
