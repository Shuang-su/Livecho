"""Fresh, owned local process supervision. No audio or scored results cross pipes."""

import os
import selectors
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .pass_control import FRAME_LIMIT, PassFailure, PassMachine, PassRequest
from .runner import PassPlan

_ROOT = Path(__file__).resolve().parents[2]
_ENTRY = _ROOT / "tools/asr_benchmark/pass_child.py"
_POLL_SECONDS = 0.02
_TERM_SECONDS = 1.0
_REAP_SECONDS = 1.0


def _spawn() -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-I", "-B", str(_ENTRY)],
        cwd=_ROOT,
        env={},
        shell=False,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        bufsize=0,
    )


@dataclass(frozen=True)
class PassControlOutcome:
    """Unscored process metadata; never a Cold/Warm row or complete Report."""

    run_id: str
    state: Literal["blocked", "control_complete"]
    reaped: Literal[True] = True


class PassSupervisor:
    def __init__(self) -> None:
        self._used = False
        self._child: subprocess.Popen[bytes] | None = None

    def close(self) -> None:
        """Idempotent for released ownership; failed reap remains owned for retry."""
        child = self._child
        if child is None:
            return
        failed = False
        try:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=_TERM_SECONDS)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=_REAP_SECONDS)
            else:
                child.wait(timeout=_REAP_SECONDS)
        except BaseException:
            failed = True
            # A failed terminate still gets an independent kill/reap attempt.
            try:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=_REAP_SECONDS)
            except BaseException:
                pass
        finally:
            for pipe in (child.stdin, child.stdout):
                if pipe is not None:
                    try:
                        pipe.close()
                    except BaseException:
                        failed = True
        if failed:
            raise PassFailure("child_cleanup_failed") from None
        self._child = None

    def run(
        self,
        plan: PassPlan,
        manifest_id: str,
        corpus_id: str,
        *,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> PassControlOutcome:
        if self._used:
            raise PassFailure("child_owner_used")
        if os.name != "posix":
            raise PassFailure("child_platform_unavailable")
        request = PassRequest(manifest_id, corpus_id, plan, uuid.uuid4().hex)
        wire = request.wire()
        self._used = True
        machine = PassMachine(request, wire, time.monotonic_ns())
        result: PassControlOutcome | None = None
        try:
            if cancelled():
                raise PassFailure("cancelled")
            # Popen itself may block in the OS. Record the returned handle before
            # cancellation/deadline checks or fallible descriptor setup.
            self._child = _spawn()
            if cancelled():
                raise PassFailure("cancelled")
            machine.check(time.monotonic_ns())
            result = self._drive(machine, wire, cancelled)
        except (OSError, ValueError):
            raise PassFailure("child_io_failed") from None
        finally:
            self.close()
        if cancelled():
            raise PassFailure("cancelled")
        machine.check(time.monotonic_ns())
        assert result is not None
        return result

    def _drive(
        self,
        machine: PassMachine,
        wire: bytes,
        cancelled: Callable[[], bool],
    ) -> PassControlOutcome:
        child = self._child
        assert child is not None and child.stdin is not None and child.stdout is not None
        os.set_blocking(child.stdin.fileno(), False)
        os.set_blocking(child.stdout.fileno(), False)
        outgoing = wire
        incoming = bytearray()
        eof = False
        writing = True
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            selector.register(child.stdin, selectors.EVENT_WRITE)
            while True:
                if cancelled():
                    raise PassFailure("cancelled")
                now = time.monotonic_ns()
                machine.check(now)
                code = child.poll()
                if code is not None and code != 0:
                    raise PassFailure("child_exit_failed")
                if eof and code is not None:
                    if machine.terminal is None or incoming or outgoing:
                        raise PassFailure("child_incomplete")
                    child.wait(timeout=_REAP_SECONDS)
                    return PassControlOutcome(machine.request.run_id, machine.terminal)
                if outgoing and not writing:
                    selector.register(child.stdin, selectors.EVENT_WRITE)
                    writing = True
                ready = selector.select(min(_POLL_SECONDS, (machine.deadline - now) / 1e9))
                for key, _ in ready:
                    if cancelled():
                        raise PassFailure("cancelled")
                    machine.check(time.monotonic_ns())
                    if key.fileobj is child.stdin:
                        try:
                            written = os.write(child.stdin.fileno(), outgoing)
                        except BlockingIOError:
                            continue
                        if written <= 0:
                            raise PassFailure("child_io_failed")
                        outgoing = outgoing[written:]
                        if not outgoing:
                            selector.unregister(child.stdin)
                            writing = False
                    else:
                        try:
                            data = os.read(child.stdout.fileno(), FRAME_LIMIT + 1 - len(incoming))
                        except BlockingIOError:
                            continue
                        if not data:
                            eof = True
                            selector.unregister(child.stdout)
                            if incoming:
                                raise PassFailure("child_metadata_invalid")
                            continue
                        incoming.extend(data)
                        while b"\n" in incoming:
                            index = incoming.index(b"\n") + 1
                            frame = bytes(incoming[:index])
                            del incoming[:index]
                            if outgoing:
                                raise PassFailure("child_phase_invalid")
                            outgoing = machine.accept(frame, time.monotonic_ns()) or b""
                        if len(incoming) >= FRAME_LIMIT:
                            raise PassFailure("child_metadata_limit")
