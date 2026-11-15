"""Fixed decoder launch and bounded cleanup. No source controls executable arguments."""

from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import sys
from contextlib import suppress
from pathlib import Path
from typing import Protocol

from .contracts import AudioError, Reason, SourceFormat
from .preflight import PIPE_CAPACITY, RuntimePermit


class Child(Protocol):
    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float) -> int: ...


def terminate_and_reap(child: Child) -> bool:
    """At most 500 ms TERM then 500 ms KILL; process identity remains a live handle."""
    try:
        if child.poll() is not None:
            return True
        child.terminate()
        try:
            child.wait(timeout=0.5)
            return True
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=0.5)
            return True
    except (OSError, subprocess.TimeoutExpired):
        return False


class ProcessGroup:
    """Only the decoder's direct watchdog parent owns this identity and reaps it."""

    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process

    def poll(self) -> int | None:
        return self.process.poll()

    def _signal(self, value: int) -> None:
        # A child that dies after this poll remains an unreaped zombie until this
        # single owner waits, so its PID cannot be reused during killpg.
        if self.process.poll() is None:
            with suppress(ProcessLookupError):
                os.killpg(self.process.pid, value)

    def terminate(self) -> None:
        self._signal(signal.SIGTERM)

    def kill(self) -> None:
        self._signal(signal.SIGKILL)

    def wait(self, timeout: float) -> int:
        return self.process.wait(timeout=timeout)


def _close(fd: int) -> None:
    with suppress(OSError):
        os.close(fd)


def _audio_pipe() -> tuple[int, int]:
    descriptors = os.pipe()
    try:
        # Only the approved Linux host path reaches here. Capacity is verified before
        # any writer receives the descriptors, not inferred from FFmpeg blocksize.
        set_size = getattr(fcntl, "F_SETPIPE_SZ")  # noqa: B009 (Linux-only capability)
        get_size = getattr(fcntl, "F_GETPIPE_SZ")  # noqa: B009 (Linux-only capability)
        fcntl.fcntl(descriptors[0], set_size, PIPE_CAPACITY)
        if fcntl.fcntl(descriptors[0], get_size) != PIPE_CAPACITY:
            raise AudioError(Reason.BUDGET_UNVERIFIED)
        return descriptors
    except (AttributeError, OSError, AudioError):
        for descriptor in descriptors:
            _close(descriptor)
        raise AudioError(Reason.BUDGET_UNVERIFIED) from None


class DecoderSupervisor:
    """Watchdog owns/reaps FFmpeg; the backend owns all audio reads/writes."""

    def __init__(self, permit: RuntimePermit, source_format: SourceFormat) -> None:
        permit.require()
        self.permit = permit
        self.source_format = source_format
        self.process: subprocess.Popen[bytes] | None = None
        self.input_fd = -1
        self.output_fd = -1
        self._liveness = -1
        self._ready = -1
        self._closed = False
        self._reaped = False
        self.failure_reason: Reason | None = None

    def start(self) -> None:
        self.permit.require()
        if self.process is not None or self._closed:
            raise AudioError(Reason.ADMISSION_CLOSED)
        descriptors: list[int] = []
        try:
            input_read, self.input_fd = _audio_pipe()
            descriptors.extend((input_read, self.input_fd))
            self.output_fd, output_write = _audio_pipe()
            descriptors.extend((self.output_fd, output_write))
            live_read, self._liveness = os.pipe()
            descriptors.extend((live_read, self._liveness))
            self._ready, ready_write = os.pipe()
            descriptors.extend((self._ready, ready_write))
            package_root = Path(__file__).resolve().parents[2]
            self.process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "livecho_backend.audio.watchdog",
                    self.permit.build.identity,
                    self.permit.host.identity,
                    str(self.source_format.sample_rate_hz),
                    str(self.source_format.channels),
                    str(input_read),
                    str(output_write),
                    str(live_read),
                    str(ready_write),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                pass_fds=(input_read, output_write, live_read, ready_write),
                env={"LANG": "C", "PYTHONPATH": str(package_root), "PYTHONDONTWRITEBYTECODE": "1"},
                start_new_session=True,
            )
            for descriptor in (input_read, output_write, live_read, ready_write):
                _close(descriptor)
                descriptors.remove(descriptor)
            os.set_blocking(self.input_fd, False)
            os.set_blocking(self.output_fd, False)
            os.set_blocking(self._ready, False)
        except (OSError, AudioError):
            for descriptor in descriptors:
                _close(descriptor)
            self.close()
            raise AudioError(Reason.DECODER_PIPE) from None

    def ready(self) -> bool:
        if self.process is None:
            raise AudioError(Reason.WATCHDOG_EXIT)
        if self._ready == -1:
            return True
        result = self.process.poll()
        if result is not None and result != 0:
            raise AudioError(Reason.WATCHDOG_EXIT)
        try:
            value = os.read(self._ready, 1)  # A fixed control byte, never decoder output.
        except BlockingIOError:
            return False
        if value != b"R":
            raise AudioError(Reason.WATCHDOG_EXIT)
        _close(self._ready)
        self._ready = -1
        return True

    def finish_input(self) -> None:
        if self.input_fd != -1:
            _close(self.input_fd)
            self.input_fd = -1

    def check(self) -> None:
        if self.process is None:
            raise AudioError(Reason.DECODER_PIPE)
        result = self.process.poll()
        if result is not None and result != 0:
            raise AudioError(Reason.DECODER_EXIT if result == 10 else Reason.WATCHDOG_EXIT)

    def completed(self) -> bool:
        self.check()
        assert self.process is not None
        return self.process.poll() == 0

    def close(self) -> bool:
        if self._closed:
            return self._reaped
        self._closed = True
        self.finish_input()
        for descriptor in (self.output_fd, self._liveness, self._ready):
            if descriptor != -1:
                _close(descriptor)
        self.output_fd = self._liveness = self._ready = -1
        if self.process is None:
            self._reaped = True
            return True
        # EOF on liveness directs the independent watchdog to TERM/KILL/reap its child.
        try:
            result = self.process.wait(timeout=1.1)
            if result == 10:
                self.failure_reason = Reason.DECODER_EXIT
            self._reaped = result in (0, 10)
        except subprocess.TimeoutExpired:
            # An unresponsive watchdog is killed; decoder PDEATHSIG also closes its
            # lifetime. Replacement stays blocked because reaping was not confirmed.
            terminate_and_reap(self.process)
            self._reaped = False
        return self._reaped
