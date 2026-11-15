"""Fixed first-party entry. No model/provider/source execution is registered."""

import sys
from pathlib import Path

# -I excludes cwd/script/user paths. Only this fixed first-party root is restored.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.asr_benchmark.pass_control import (
    REQUEST_LIMIT,
    PassFailure,
    event,
    read_request,
    request_digest,
)


def main() -> int:
    if len(sys.argv) != 1:
        return 2
    try:
        data = sys.stdin.buffer.readline(REQUEST_LIMIT + 1)
        request = read_request(data)
        # Deliberately empty execution registry: IDs never become import names,
        # file paths, commands or evidence of approval. Do not import a provider.
        sys.stdout.buffer.write(event(request, request_digest(data), 0, "blocked"))
        sys.stdout.buffer.flush()
        return 0
    except (PassFailure, OSError):
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
