"""Fixed internal watchdog entry point. It never reads, writes, or holds audio samples."""

from __future__ import annotations

import ctypes
import os
import resource
import select
import signal
import subprocess
import sys
from functools import partial

from .contracts import AudioError, SourceFormat
from .preflight import fixed_arguments, preflight
from .supervisor import ProcessGroup, _close, terminate_and_reap


def _decoder_limits(expected_parent: int) -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if os.getppid() != expected_parent:
        os._exit(70)
    libc = ctypes.CDLL(None, use_errno=True)
    # Linux PR_SET_PDEATHSIG closes the decoder lifetime if its watchdog dies.
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != expected_parent:
        os._exit(70)


def run(arguments: list[str]) -> int:
    if len(arguments) != 8:
        return 70
    child: subprocess.Popen[bytes] | None = None
    try:
        permit = preflight(arguments[0], arguments[1])
        source_format = SourceFormat.model_validate(
            {
                "encoding": "pcm_s16le",
                "sample_rate_hz": int(arguments[2]),
                "channels": int(arguments[3]),
            }
        )
        input_read, output_write, live_read, ready_write = map(int, arguments[4:])
        if len({input_read, output_write, live_read, ready_write}) != 4:
            return 70
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # No data is admitted before R. A backend that already died never gains a child.
        readable, _, _ = select.select([live_read], [], [], 0)
        if readable:
            return 70
        child = subprocess.Popen(
            fixed_arguments(permit.build, source_format),
            stdin=input_read,
            stdout=output_write,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
            preexec_fn=partial(_decoder_limits, os.getpid()),
            env={"LANG": "C"},
        )
        _close(input_read)
        _close(output_write)
        os.write(ready_write, b"R")
        _close(ready_write)
        group = ProcessGroup(child)
        while child.poll() is None:
            readable, _, _ = select.select([live_read], [], [], 0.01)
            if readable:
                # Any liveness-pipe event means stop; no control instruction parser.
                return 0 if terminate_and_reap(group) else 71
        return 0 if child.returncode == 0 else 10
    except (AudioError, OSError, ValueError):
        return 70
    finally:
        if child is not None and child.poll() is None:
            terminate_and_reap(ProcessGroup(child))


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
