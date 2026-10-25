"""Original closed metadata and OS-process controls; no model/audio execution."""

import dataclasses
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

import pytest

from tools.asr_benchmark import pass_control as control
from tools.asr_benchmark import pass_supervisor as supervisor
from tools.asr_benchmark.contracts import NS
from tools.asr_benchmark.pass_control import PassFailure, PassMachine, PassRequest, event
from tools.asr_benchmark.runner import PassPlan


def plan() -> PassPlan:
    scripts = tuple(f"script-{index:02}" for index in range(60))
    return PassPlan("Qwen/Qwen3-ASR-1.7B", 2, 1, 0, scripts[0], 3, scripts)


def request() -> PassRequest:
    return PassRequest("reviewed-manifest", "reviewed-corpus", plan(), "a" * 32)


def machine() -> PassMachine:
    req = request()
    return PassMachine(req, req.wire(), 0)


def send(fsm: PassMachine, kind: str, now: int = 0, **extra: int) -> bytes | None:
    return fsm.accept(event(fsm.request, fsm.digest, fsm.seq, kind, **extra), now)


def enter(fsm: PassMachine, phase: str) -> None:
    send(fsm, "ready")
    if phase == "load":
        return
    send(fsm, "loaded")
    send(fsm, "input")
    if phase == "input":
        return
    send(fsm, "progress", pts_ns=0)
    send(fsm, "input_done")
    send(fsm, "call")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model", "other"),
        ("window_seconds", True),
        ("window_seconds", 3),
        ("repetition", True),
        ("repetition", 0),
        ("order", True),
        ("order", 1),
        ("warmup_count", 0),
        ("warmup_count", True),
        ("silence_duration_ns", True),
        ("silence_duration_ns", 1),
        ("conditions", ("noise", "clean")),
        ("cold_script_id", "unknown"),
        ("script_ids", ("only-one",)),
        ("script_ids", tuple("duplicate" for _ in range(60))),
        ("script_ids", tuple(f"/tmp/{index}" for index in range(60))),
        ("script_ids", tuple(reversed(plan().script_ids))),
    ],
)
def test_plan_revalidated_before_spawn(
    field: str,
    value: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(supervisor, "_spawn", lambda: pytest.fail("spawned"))
    with pytest.raises(PassFailure, match="pass_plan_invalid"):
        supervisor.PassSupervisor().run(dataclasses.replace(plan(), **{field: value}), "id", "id")


@pytest.mark.parametrize("identifier", ["/tmp/path", "module:run", "https://host", "x" * 97, ""])
def test_ids_are_not_paths_or_commands(identifier: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supervisor, "_spawn", lambda: pytest.fail("spawned"))
    with pytest.raises(PassFailure):
        supervisor.PassSupervisor().run(plan(), identifier, "id")


def test_plan_order_and_full_wire_binding() -> None:
    req = dataclasses.replace(request(), plan=dataclasses.replace(plan(), repetition=2, order=1))
    assert control.read_request(req.wire()) == req
    fsm = machine()
    altered = json.loads(event(fsm.request, fsm.digest, 0, "ready"))
    altered["request_sha256"] = control.request_digest(req.wire())
    with pytest.raises(PassFailure, match="metadata"):
        fsm.accept(control.encode(altered, 512), 0)


@pytest.mark.parametrize(
    "data",
    [
        b"{}",
        b"[]\n",
        b'{"x":1,"x":2}\n',
        b'{"x":NaN}\n',
        b"\xff\n",
        b"x" * 513 + b"\n",
        b"{}\n{}\n",
    ],
)
def test_malformed_or_unclosed_metadata(data: bytes) -> None:
    with pytest.raises(PassFailure):
        machine().accept(data, 0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("seq", True),
        ("seq", 1),
        ("run_id", "b" * 32),
        ("kind", "arbitrary"),
        ("request_sha256", "0" * 64),
        ("error", "private arbitrary message"),
        ("pts_ns", 0),
    ],
)
def test_closed_event_identity(field: str, value: Any) -> None:
    fsm = machine()
    data = json.loads(event(fsm.request, fsm.digest, 0, "ready"))
    data[field] = value
    with pytest.raises(PassFailure):
        fsm.accept(control.encode(data, 512), 0)


@pytest.mark.parametrize(
    ("phase", "seconds", "reason"),
    [
        ("load", 30, "cached_load_timeout"),
        ("input", 2, "input_stalled"),
        ("call", 10, "provider_timeout"),
    ],
)
def test_absolute_phase_deadlines(phase: str, seconds: int, reason: str) -> None:
    fsm = machine()
    enter(fsm, phase)
    fsm.check(seconds * NS - 1)
    with pytest.raises(PassFailure, match=reason):
        fsm.check(seconds * NS)


def test_progress_renews_only_active_input_and_exact_pts() -> None:
    fsm = machine()
    enter(fsm, "input")
    send(fsm, "progress", NS, pts_ns=0)
    assert fsm.deadline == 3 * NS
    for pts in (0, -1, True, 2 * NS + 1):
        fresh = machine()
        enter(fresh, "input")
        send(fresh, "progress", pts_ns=0)
        with pytest.raises(PassFailure, match="progress"):
            send(fresh, "progress", NS, pts_ns=pts)
    send(fsm, "input_done", NS)
    send(fsm, "call", NS)
    assert fsm.deadline == 11 * NS
    with pytest.raises(PassFailure, match="phase"):
        send(fsm, "progress", 2 * NS, pts_ns=1)


@pytest.mark.parametrize("kind", ["ready", "input", "call", "finished", "blocked"])
def test_overlap_and_duplicate_phases_rejected(kind: str) -> None:
    fsm = machine()
    enter(fsm, "load")
    with pytest.raises(PassFailure):
        send(fsm, kind, NS)
    assert fsm.deadline == 30 * NS


def test_late_ready_backward_clock_event_count_and_terminal() -> None:
    with pytest.raises(PassFailure, match="timeout"):
        send(machine(), "ready", 5 * NS)
    fsm = machine()
    fsm.check(1)
    with pytest.raises(PassFailure, match="clock"):
        fsm.check(0)
    fsm = machine()
    fsm.seq = control.EVENT_LIMIT
    with pytest.raises(PassFailure, match="metadata"):
        send(fsm, "ready")
    fsm = machine()
    send(fsm, "blocked")
    with pytest.raises(PassFailure, match="metadata"):
        send(fsm, "blocked")


def spawn_fixture(monkeypatch: pytest.MonkeyPatch, scenario: str) -> list[subprocess.Popen[bytes]]:
    children: list[subprocess.Popen[bytes]] = []

    def spawn() -> subprocess.Popen[bytes]:
        child = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-B",
                str(Path(__file__).with_name("metadata_pass_child.py")),
                scenario,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={},
            bufsize=0,
        )
        children.append(child)
        return child

    monkeypatch.setattr(supervisor, "_spawn", spawn)
    return children


def assert_reaped(
    children: list[subprocess.Popen[bytes]],
    owner: supervisor.PassSupervisor,
) -> None:
    assert len(children) == 1 and children[0].poll() is not None
    assert children[0].stdin is not None and children[0].stdin.closed
    assert children[0].stdout is not None and children[0].stdout.closed
    assert owner._child is None
    owner.close()


def test_fixed_entry_empty_registry_fresh_and_no_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    original = subprocess.Popen
    calls: list[tuple[Any, Any]] = []

    def capture(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", capture)
    first, second = supervisor.PassSupervisor(), supervisor.PassSupervisor()
    one = first.run(plan(), "reviewed-id", "reviewed-corpus")
    two = second.run(plan(), "reviewed-id", "reviewed-corpus")
    assert one.state == two.state == "blocked" and one.run_id != two.run_id
    assert one.reaped and two.reaped and len(calls) == 2
    for args, kwargs in calls:
        assert args == ([sys.executable, "-I", "-B", str(supervisor._ENTRY)],)
        assert kwargs["env"] == {} and kwargs["shell"] is False and kwargs["close_fds"]
        assert kwargs["cwd"] == supervisor._ROOT and kwargs["stderr"] == subprocess.DEVNULL
    with pytest.raises(PassFailure, match="owner_used"):
        first.run(plan(), "id", "id")


def test_control_completion_is_unscored_and_reaped(monkeypatch: pytest.MonkeyPatch) -> None:
    children = spawn_fixture(monkeypatch, "valid")
    owner = supervisor.PassSupervisor()
    result = owner.run(plan(), "id", "id")
    assert result.state == "control_complete"
    assert set(dataclasses.asdict(result)) == {"run_id", "state", "reaped"}
    assert_reaped(children, owner)


@pytest.mark.parametrize(
    "scenario",
    ["bad_exit", "trailing", "duplicate", "empty", "oversize", "premature"],
)
def test_terminal_or_pipe_faults_never_complete(
    scenario: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    children = spawn_fixture(monkeypatch, scenario)
    owner = supervisor.PassSupervisor()
    with pytest.raises(PassFailure):
        owner.run(plan(), "id", "id")
    assert_reaped(children, owner)


@pytest.mark.parametrize("scenario", ["hang", "ignore_term", "partial", "terminal_hang"])
def test_timeout_partial_and_terminal_hang_reaped(
    scenario: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    children = spawn_fixture(monkeypatch, scenario)
    original = PassMachine.accept

    def accept(self: PassMachine, data: bytes, now: int) -> bytes | None:
        result = original(self, data, now)
        self.deadline = min(self.deadline, now + 50_000_000)
        return result

    monkeypatch.setattr(PassMachine, "accept", accept)
    monkeypatch.setattr(control, "STARTUP_NS", 500_000_000)
    monkeypatch.setattr(supervisor, "_TERM_SECONDS", 0.05)
    owner = supervisor.PassSupervisor()
    with pytest.raises(PassFailure, match="timeout"):
        owner.run(plan(), "id", "id")
    assert_reaped(children, owner)
    if scenario == "ignore_term":
        assert children[0].returncode == -9


def test_cancellation_before_and_immediately_after_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supervisor, "_spawn", lambda: pytest.fail("spawned"))
    with pytest.raises(PassFailure, match="cancelled"):
        supervisor.PassSupervisor().run(plan(), "id", "id", cancelled=lambda: True)
    children = spawn_fixture(monkeypatch, "hang")
    owner = supervisor.PassSupervisor()
    with pytest.raises(PassFailure, match="cancelled"):
        owner.run(plan(), "id", "id", cancelled=lambda: bool(children))
    assert_reaped(children, owner)


def test_cancellation_callback_failure_still_reaps(monkeypatch: pytest.MonkeyPatch) -> None:
    children = spawn_fixture(monkeypatch, "hang")
    owner = supervisor.PassSupervisor()

    def cancel() -> bool:
        if children:
            raise RuntimeError("local callback")
        return False

    with pytest.raises(RuntimeError, match="callback"):
        owner.run(plan(), "id", "id", cancelled=cancel)
    assert_reaped(children, owner)


def test_setup_failure_and_late_spawn_are_owned(monkeypatch: pytest.MonkeyPatch) -> None:
    children = spawn_fixture(monkeypatch, "hang")
    owner = supervisor.PassSupervisor()

    def fail(*args: Any) -> None:
        raise OSError("private path")

    monkeypatch.setattr(os, "set_blocking", fail)
    with pytest.raises(PassFailure, match="^child_io_failed$"):
        owner.run(plan(), "id", "id")
    assert_reaped(children, owner)
    monkeypatch.undo()
    children = spawn_fixture(monkeypatch, "hang")
    spawn = supervisor._spawn

    def late() -> subprocess.Popen[bytes]:
        child = spawn()
        time.sleep(0.01)
        return child

    monkeypatch.setattr(supervisor, "_spawn", late)
    monkeypatch.setattr(control, "STARTUP_NS", 1_000_000)
    owner = supervisor.PassSupervisor()
    with pytest.raises(PassFailure, match="operational_timeout"):
        owner.run(plan(), "id", "id")
    assert_reaped(children, owner)


class CleanupChild:
    def __init__(self) -> None:
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
        self.returncode: int | None = None
        self.fail = True
        self.calls: list[str] = []

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.calls.append("terminate")

    def kill(self) -> None:
        self.calls.append("kill")

    def wait(self, timeout: float) -> int:
        self.calls.append("wait")
        if self.fail:
            raise subprocess.TimeoutExpired("private", timeout)
        self.returncode = 0
        return 0


def test_cleanup_failure_retains_only_owned_handle_for_retry() -> None:
    owner = supervisor.PassSupervisor()
    child = CleanupChild()
    owner._child = child  # type: ignore[assignment]
    with pytest.raises(PassFailure, match="cleanup_failed"):
        owner.close()
    assert cast(Any, owner._child) is child and child.stdin.closed and child.stdout.closed
    assert child.calls[:3] == ["terminate", "wait", "kill"]
    child.fail = False
    owner.close()
    assert owner._child is None
    calls = list(child.calls)
    owner.close()
    assert child.calls == calls


@pytest.mark.parametrize("field", ["script_ids", "model", "manifest_id"])
def test_request_rejects_before_recursive_copy_or_encoding(
    field: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(control, "encode", lambda *args: pytest.fail("encoded"))
    monkeypatch.setattr(control, "asdict", lambda *args: pytest.fail("copied"))
    if field == "manifest_id":
        req = dataclasses.replace(request(), manifest_id="x" * 97)
    else:
        bad: dict[str, Any] = {
            "script_ids": tuple(f"id{index}" for index in range(61)),
            "model": {"nested": []},
        }
        req = dataclasses.replace(
            request(), plan=dataclasses.replace(plan(), **{field: bad[field]})
        )
    with pytest.raises(PassFailure):
        req.wire()


def test_late_cleanup_and_post_cleanup_cancel_cannot_deliver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    children = spawn_fixture(monkeypatch, "valid")
    owner = supervisor.PassSupervisor()
    original = owner.close
    clock = time.monotonic_ns
    late = False

    def close() -> None:
        nonlocal late
        original()
        late = True

    monkeypatch.setattr(owner, "close", close)
    monkeypatch.setattr(time, "monotonic_ns", lambda: clock() + (3 * NS if late else 0))
    with pytest.raises(PassFailure, match="operational_timeout"):
        owner.run(plan(), "id", "id")
    assert_reaped(children, owner)


def test_partial_writes_and_reads_preserve_framing(monkeypatch: pytest.MonkeyPatch) -> None:
    children = spawn_fixture(monkeypatch, "valid")
    owner = supervisor.PassSupervisor()
    read, write = os.read, os.write

    def small_read(fd: int, count: int) -> bytes:
        return read(fd, min(count, 7))

    def small_write(fd: int, data: bytes) -> int:
        return write(fd, data[:11])

    monkeypatch.setattr(os, "read", small_read)
    monkeypatch.setattr(os, "write", small_write)
    assert owner.run(plan(), "id", "id").state == "control_complete"
    assert_reaped(children, owner)


def test_frame_and_request_exact_boundaries() -> None:
    assert control.decode(b" " * 509 + b"{}\n", 512) == {}
    with pytest.raises(PassFailure, match="metadata_invalid"):
        control.decode(b" " * 510 + b"{}\n", 512)
    with pytest.raises(PassFailure, match="metadata_invalid"):
        control.read_request(b" " * control.REQUEST_LIMIT + b"{}\n")
    data = request().wire()
    assert control.request_digest(data) != control.request_digest(b" " + data)


def test_runtime_cleanup_failure_and_interrupt_are_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    children = spawn_fixture(monkeypatch, "valid")
    owner = supervisor.PassSupervisor()
    original = owner.close

    def fail_close() -> None:
        original()
        raise PassFailure("child_cleanup_failed")

    monkeypatch.setattr(owner, "close", fail_close)
    with pytest.raises(PassFailure, match="cleanup_failed"):
        owner.run(plan(), "id", "id")
    assert children[0].poll() == 0 and owner._child is None
    monkeypatch.undo()
    children = spawn_fixture(monkeypatch, "hang")
    owner = supervisor.PassSupervisor()

    def interrupt() -> bool:
        if children:
            raise KeyboardInterrupt
        return False

    with pytest.raises(KeyboardInterrupt):
        owner.run(plan(), "id", "id", cancelled=interrupt)
    assert_reaped(children, owner)
    monkeypatch.undo()
    children = spawn_fixture(monkeypatch, "valid")
    owner = supervisor.PassSupervisor()
    with pytest.raises(PassFailure, match="cancelled"):
        owner.run(plan(), "id", "id", cancelled=lambda: bool(children) and owner._child is None)
    assert_reaped(children, owner)
