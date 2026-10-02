"""Original metadata-only test child; never selected by the production entry."""

import json
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.asr_benchmark.pass_control import (
    REQUEST_LIMIT,
    event,
    read_request,
    request_digest,
)


def main() -> int:
    scenario = sys.argv[1]
    data = sys.stdin.buffer.readline(REQUEST_LIMIT + 1)
    request = read_request(data)
    digest = request_digest(data)
    seq = 0

    def send(kind: str, **extra: int) -> None:
        nonlocal seq
        sys.stdout.buffer.write(event(request, digest, seq, kind, **extra))
        sys.stdout.buffer.flush()
        seq += 1

    def grant(phase: str) -> None:
        value = json.loads(sys.stdin.buffer.readline(513))
        assert value == {
            "run_id": request.run_id,
            "request_sha256": digest,
            "seq": seq - 1,
            "grant": phase,
        }

    if scenario == "ignore_term":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if scenario in ("hang", "ignore_term"):
        send("ready")
        grant("load")
        time.sleep(30)
        return 0
    if scenario == "partial":
        sys.stdout.buffer.write(b'{"seq":')
        sys.stdout.buffer.flush()
        time.sleep(30)
        return 0
    if scenario == "oversize":
        sys.stdout.buffer.write(b"x" * 513)
        sys.stdout.buffer.flush()
        return 0
    if scenario == "premature":
        sys.stdout.buffer.write(
            event(request, digest, 0, "ready") + event(request, digest, 1, "loaded")
        )
        sys.stdout.buffer.flush()
        return 0
    if scenario == "bad_exit":
        send("blocked")
        return 9
    if scenario == "terminal_hang":
        send("blocked")
        time.sleep(30)
        return 0
    if scenario == "trailing":
        send("blocked")
        sys.stdout.buffer.write(b"extra")
        sys.stdout.buffer.flush()
        return 0
    if scenario == "duplicate":
        send("blocked")
        send("blocked")
        return 0
    if scenario == "empty":
        return 0
    send("ready")
    grant("load")
    send("loaded")
    send("input")
    grant("input")
    send("progress", pts_ns=0)
    send("progress", pts_ns=1)
    send("input_done")
    send("call")
    grant("call")
    send("called")
    send("finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
