"""Original metadata/process doubles; no host queries or model imports are required."""

import dataclasses
import os
import platform
import selectors
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any, cast

import pytest
from pydantic import ValidationError

from tools.asr_benchmark import machine_inventory as inventory
from tools.asr_benchmark.contracts import NS, Machine, PrivacyEvidence


class Clock:
    now = 0
    step = 10_000_000

    def __call__(self) -> int:
        return self.now


class Pipe:
    def __init__(self, close_hook: Callable[[], None]):
        self.closed = False
        self.close_hook = close_hook

    def fileno(self) -> int:
        return 123

    def close(self) -> None:
        self.closed = True
        self.close_hook()


@dataclasses.dataclass
class Behavior:
    output: bytes = b"32\n"
    code: int = 0
    chunk: int = 128
    hang: bool = False
    ignore_term: bool = False
    fail_reap: bool = False
    close_hook: Callable[[], None] = lambda: None


class Child:
    def __init__(self, behavior: Behavior):
        self.behavior = behavior
        self.stdout = Pipe(behavior.close_hook)
        self.remaining = behavior.output
        self.returncode: int | None = None
        self.calls: list[str] = []
        self.read_sizes: list[int] = []

    def read(self, count: int) -> bytes:
        self.read_sizes.append(count)
        count = min(count, self.behavior.chunk)
        value, self.remaining = self.remaining[:count], self.remaining[count:]
        if not value:
            self.returncode = self.behavior.code
        return value

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float) -> int:
        self.calls.append("wait")
        if self.behavior.fail_reap or self.returncode is None:
            raise subprocess.TimeoutExpired("not-retained-in-result", timeout)
        return self.returncode

    def terminate(self) -> None:
        self.calls.append("terminate")
        if not self.behavior.ignore_term:
            self.returncode = -15

    def kill(self) -> None:
        self.calls.append("kill")
        if not self.behavior.fail_reap:
            self.returncode = -9


class Selector:
    def __init__(self, factory: "Factory"):
        self.factory = factory
        self.pipe: Pipe | None = None
        self.closed = False

    def __enter__(self) -> "Selector":
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def register(self, pipe: Pipe, events: int) -> None:
        assert events == selectors.EVENT_READ
        self.pipe = pipe

    def unregister(self, pipe: Pipe) -> None:
        assert self.pipe is pipe
        self.pipe = None

    def select(self, timeout: float) -> list[tuple[object, int]]:
        assert 0 <= timeout <= 0.02
        self.factory.clock.now += self.factory.clock.step
        child = self.factory.children[-1]
        return [] if child.behavior.hang or self.pipe is None else [(self.pipe, 1)]


class Factory:
    def __init__(self, monkeypatch: pytest.MonkeyPatch):
        self.clock = Clock()
        self.fields: list[str] = []
        self.children: list[Child] = []
        self.selectors: list[Selector] = []
        self.behaviors: dict[str, Behavior] = {
            "cpu_cores": Behavior(),
            "physical_ram_bytes": Behavior(b"137438953472\n"),
            "os_build": Behavior(b"25A100\n"),
        }
        self.spawn_hook: Callable[[], None] = lambda: None
        monkeypatch.setattr(inventory, "_spawn", self.spawn)
        monkeypatch.setattr(sys, "platform", "darwin")
        monkeypatch.setattr(platform, "python_version", lambda: "3.12.10")
        monkeypatch.setattr(time, "monotonic_ns", self.clock)
        monkeypatch.setattr(selectors, "DefaultSelector", self.selector)
        monkeypatch.setattr(os, "set_blocking", lambda *args: None)
        monkeypatch.setattr(os, "read", lambda fd, count: self.children[-1].read(count))

    def spawn(self, field: inventory.QueryField) -> Any:
        self.fields.append(field)
        child = Child(self.behaviors[field])
        self.children.append(child)
        self.spawn_hook()
        return child

    def selector(self) -> Any:
        selector = Selector(self)
        self.selectors.append(selector)
        return selector

    def assert_closed(self, owner: inventory.MachineInventoryCollector) -> None:
        assert all(child.stdout.closed and child.poll() is not None for child in self.children)
        assert all(selector.closed for selector in self.selectors)
        assert owner._child is None


def reasons(snapshot: inventory.InventorySnapshot) -> dict[str, str]:
    return {item.field: item.reason for item in snapshot.missing}


def test_fixed_queries_sources_and_incomplete_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    owner = inventory.MachineInventoryCollector()
    snapshot = owner.collect()
    assert snapshot.state == "incomplete"
    assert snapshot.observations.model_dump() == {
        "cpu_cores": 32,
        "physical_ram_bytes": 137438953472,
        "os_build": "25A100",
        "python_version": "3.12.10",
    }
    assert snapshot.sources.model_dump() == {
        "cpu_cores": "sysctl-hw.physicalcpu_max",
        "physical_ram_bytes": "sysctl-hw.memsize",
        "os_build": "sw_vers-buildVersion",
        "python_version": "platform.python_version",
    }
    assert len(snapshot.missing) == 13
    assert set(reasons(snapshot).values()) == {"not_collected"}
    assert set(reasons(snapshot)) == set(Machine.model_fields) - set(
        snapshot.observations.model_dump()
    )
    assert 0 == snapshot.started_ns < snapshot.finished_ns < 6 * NS
    assert factory.fields == ["cpu_cores", "physical_ram_bytes", "os_build"]
    factory.assert_closed(owner)
    owner.close()
    with pytest.raises(inventory.InventoryFailure, match="owner_used"):
        owner.collect()
    for model in (Machine, PrivacyEvidence):
        with pytest.raises(ValidationError):
            model.model_validate(snapshot.model_dump())


def test_spawn_has_only_fixed_readonly_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {
        "cpu_cores": ("/usr/sbin/sysctl", "-n", "hw.physicalcpu_max"),
        "physical_ram_bytes": ("/usr/sbin/sysctl", "-n", "hw.memsize"),
        "os_build": ("/usr/bin/sw_vers", "--buildVersion"),
    }
    calls: list[tuple[object, dict[str, Any]]] = []

    def popen(args: object, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        return object()

    monkeypatch.setattr(subprocess, "Popen", popen)
    for field, command in expected.items():
        inventory._spawn(cast(inventory.QueryField, field))
        args, kwargs = calls[-1]
        assert args == command
        assert kwargs == {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
            "shell": False,
            "env": {},
            "cwd": "/",
            "close_fds": True,
            "bufsize": 0,
        }
    for unknown in ("kern.hostname", "-a", "https://host", "/tmp/run", None, True):
        with pytest.raises(inventory.InventoryFailure, match="query_invalid"):
            inventory._spawn(cast(Any, unknown))
    assert len(calls) == 3


@pytest.mark.parametrize(
    "field,output",
    [
        ("cpu_cores", b"0\n"),
        ("cpu_cores", b"-1\n"),
        ("cpu_cores", b"4097\n"),
        ("cpu_cores", b"32 64\n"),
        ("cpu_cores", b"032\n"),
        ("cpu_cores", b"32\r\n"),
        ("cpu_cores", b"32\nextra\n"),
        ("cpu_cores", b"\xff\n"),
        ("cpu_cores", b"32"),
        ("cpu_cores", b""),
        ("cpu_cores", b"true\n"),
        ("cpu_cores", b" 32\n"),
        ("cpu_cores", b"NaN\n"),
        ("physical_ram_bytes", b"1152921504606846977\n"),
        ("physical_ram_bytes", b"128 GiB\n"),
        ("os_build", b"macOS 26\n"),
        ("os_build", b"private-hostname\n"),
        ("os_build", b"25A100\nusername\n"),
        ("os_build", b"x" * 129),
        ("os_build", b"1" * 128),
    ],
)
def test_invalid_outputs_are_missing_without_raw_payload(
    field: str,
    output: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Factory(monkeypatch)
    factory.behaviors[field] = Behavior(output)
    owner = inventory.MachineInventoryCollector()
    snapshot = owner.collect()
    assert getattr(snapshot.observations, field) is None
    assert reasons(snapshot)[field] == "output_invalid"
    assert "private-hostname" not in snapshot.model_dump_json()
    assert "username" not in snapshot.model_dump_json()
    assert all(size <= 129 for child in factory.children for size in child.read_sizes)
    factory.assert_closed(owner)


@pytest.mark.parametrize(
    "field,value",
    [
        ("cpu_cores", 4096),
        ("physical_ram_bytes", 2**60),
        ("os_build", "25A100a"),
    ],
)
def test_exact_parsing_caps(field: str, value: int | str, monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    factory.behaviors[field] = Behavior(f"{value}\n".encode())
    snapshot = inventory.MachineInventoryCollector().collect()
    assert getattr(snapshot.observations, field) == value


@pytest.mark.parametrize("value", ["", "3.12", "3.12.1 private", "x" * 33, True, None])
def test_invalid_python_is_missing(value: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    Factory(monkeypatch)
    monkeypatch.setattr(platform, "python_version", lambda: value)
    snapshot = inventory.MachineInventoryCollector().collect()
    assert snapshot.observations.python_version is None
    assert reasons(snapshot)["python_version"] == "output_invalid"


def test_unsupported_platform_and_python_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    monkeypatch.setattr(sys, "platform", "linux")
    snapshot = inventory.MachineInventoryCollector().collect()
    assert not factory.children
    assert snapshot.observations.python_version == "3.12.10"
    assert {reasons(snapshot)[key] for key in factory.behaviors} == {"platform_unsupported"}

    def fail() -> str:
        raise OSError("arbitrary version diagnostic")

    monkeypatch.setattr(platform, "python_version", fail)
    snapshot = inventory.MachineInventoryCollector().collect()
    assert reasons(snapshot)["python_version"] == "python_unavailable"
    assert "diagnostic" not in snapshot.model_dump_json()


@pytest.mark.parametrize("failure", [FileNotFoundError, PermissionError, ValueError])
def test_query_spawn_failures_are_stable_missing(
    failure: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Factory(monkeypatch)

    def spawn(field: str) -> Any:
        raise failure("private path or environment")

    monkeypatch.setattr(inventory, "_spawn", spawn)
    snapshot = inventory.MachineInventoryCollector().collect()
    expected = "query_unavailable" if failure is FileNotFoundError else "query_failed"
    assert reasons(snapshot)["cpu_cores"] == expected
    assert "private" not in snapshot.model_dump_json()


def test_nonzero_exit_after_valid_stdout_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    factory.behaviors["cpu_cores"] = Behavior(code=1)
    owner = inventory.MachineInventoryCollector()
    snapshot = owner.collect()
    assert reasons(snapshot)["cpu_cores"] == "query_failed"
    factory.assert_closed(owner)


def test_partial_output_never_renews_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    factory.clock.step = NS
    factory.behaviors["cpu_cores"] = Behavior(chunk=1)
    owner = inventory.MachineInventoryCollector()
    snapshot = owner.collect()
    assert snapshot.observations.cpu_cores is None
    assert reasons(snapshot)["cpu_cores"] == "query_timeout"
    factory.assert_closed(owner)


@pytest.mark.parametrize("where", ["spawn", "close"])
def test_late_query_value_rejected_and_remaining_budget_preserved(
    where: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Factory(monkeypatch)

    def delay() -> None:
        factory.clock.now += 2 * NS

    if where == "spawn":
        factory.spawn_hook = lambda: delay() if len(factory.children) == 1 else None
    else:
        factory.behaviors["cpu_cores"].close_hook = delay
    owner = inventory.MachineInventoryCollector()
    snapshot = owner.collect()
    assert reasons(snapshot)["cpu_cores"] == "query_timeout"
    assert snapshot.observations.physical_ram_bytes == 137438953472
    factory.assert_closed(owner)


def test_total_expiry_skips_remaining_spawns(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)

    def expire() -> None:
        factory.clock.now = 6 * NS

    factory.behaviors["cpu_cores"].close_hook = expire
    owner = inventory.MachineInventoryCollector()
    snapshot = owner.collect()
    assert factory.fields == ["cpu_cores"]
    assert snapshot.observations.cpu_cores is None
    assert reasons(snapshot)["physical_ram_bytes"] == "collection_timeout"
    assert reasons(snapshot)["os_build"] == "collection_timeout"
    factory.assert_closed(owner)


def test_python_late_result_rejected_before_any_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)

    def late() -> str:
        factory.clock.now = 6 * NS
        return "3.12.10"

    monkeypatch.setattr(platform, "python_version", late)
    snapshot = inventory.MachineInventoryCollector().collect()
    assert snapshot.observations.python_version is None and not factory.children
    assert all(
        reasons(snapshot)[key] == "collection_timeout"
        for key in (
            "cpu_cores",
            "physical_ram_bytes",
            "os_build",
            "python_version",
        )
    )


@pytest.mark.parametrize("where", ["before", "spawn", "read", "close"])
def test_cancel_never_delivers_snapshot(where: str, monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    owner = inventory.MachineInventoryCollector()

    def cancelled() -> bool:
        if where == "before":
            return True
        if not factory.children:
            return False
        child = factory.children[0]
        return {"spawn": True, "read": bool(child.read_sizes), "close": child.stdout.closed}[where]

    with pytest.raises(inventory.InventoryFailure, match="cancelled"):
        owner.collect(cancelled=cancelled)
    factory.assert_closed(owner)
    assert len(factory.children) == (0 if where == "before" else 1)


@pytest.mark.parametrize("kind", [OSError, ValueError])
@pytest.mark.parametrize("source", ["cancel", "clock"])
def test_query_callback_failures_are_terminal_not_field_missing(
    kind: type[Exception],
    source: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Factory(monkeypatch)
    owner = inventory.MachineInventoryCollector()
    raised = False

    def callback() -> bool:
        nonlocal raised
        if factory.children and not raised:
            raised = True
            raise kind("private exception")
        return False

    def clock() -> int:
        callback()
        return factory.clock.now

    if source == "clock":
        monkeypatch.setattr(time, "monotonic_ns", clock)
    with pytest.raises(
        inventory.InventoryFailure, match="inventory_(callback_failed|clock_invalid)"
    ):
        owner.collect(cancelled=callback if source == "cancel" else lambda: False)
    assert raised
    factory.assert_closed(owner)
    assert len(factory.children) == 1


def test_kill_and_cleanup_failure_keep_owned_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    factory.behaviors["cpu_cores"] = Behavior(hang=True, ignore_term=True, fail_reap=True)
    owner = inventory.MachineInventoryCollector()
    with pytest.raises(inventory.InventoryFailure, match="cleanup_failed"):
        owner.collect()
    child = factory.children[0]
    assert cast(Any, owner._child) is child and child.stdout.closed
    assert child.calls[:3] == ["terminate", "wait", "kill"]
    with pytest.raises(inventory.InventoryFailure, match="owner_used"):
        owner.collect()
    child.behavior.fail_reap = False
    owner.close()
    factory.assert_closed(owner)
    before = list(child.calls)
    owner.close()
    assert child.calls == before


def test_snapshot_cannot_gain_extra_fields_or_change_missing_reasons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Factory(monkeypatch)
    snapshot = inventory.MachineInventoryCollector().collect().model_dump()
    for field, value in (("state", "complete"), ("chip", "Apple M3 Ultra"), ("hostname", "host")):
        with pytest.raises(ValidationError):
            inventory.InventorySnapshot.model_validate({**snapshot, field: value})
    with pytest.raises(ValidationError):
        inventory.InventorySnapshot.model_validate({**snapshot, "missing": ()})
    missing = list(snapshot["missing"])
    missing[0] = {**missing[0], "reason": "query_failed"}
    with pytest.raises(ValidationError):
        inventory.InventorySnapshot.model_validate({**snapshot, "missing": tuple(missing)})


@pytest.mark.parametrize("value", [True, 0, -1, 4097, 32.0])
def test_constructed_observations_revalidate(
    value: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Factory(monkeypatch)
    snapshot = inventory.MachineInventoryCollector().collect().model_dump()
    observations = inventory.InventoryObservations.model_construct(
        **{**snapshot["observations"], "cpu_cores": value}
    )
    with pytest.raises(ValidationError):
        inventory.InventorySnapshot.model_validate({**snapshot, "observations": observations})


def test_callback_type_and_clock_regression_are_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    with pytest.raises(inventory.InventoryFailure, match="callback_failed"):
        inventory.MachineInventoryCollector().collect(cancelled=lambda: cast(Any, 1))
    assert not factory.children
    owner = inventory.MachineInventoryCollector()
    owner._last_now = 1
    with pytest.raises(inventory.InventoryFailure, match="clock_invalid"):
        owner.collect()
    assert not factory.children


def test_eof_before_exit_still_times_out_and_reaps(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = Factory(monkeypatch)
    original_read = Child.read

    def read(child: Child, count: int) -> bytes:
        data = original_read(child, count)
        if child is factory.children[0] and not data:
            child.returncode = None
        return data

    monkeypatch.setattr(Child, "read", read)
    owner = inventory.MachineInventoryCollector()
    snapshot = owner.collect()
    assert reasons(snapshot)["cpu_cores"] == "query_timeout"
    factory.assert_closed(owner)


def test_close_error_never_yields_snapshot_and_retry_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Factory(monkeypatch)
    count = 0

    def close_error() -> None:
        nonlocal count
        count += 1
        if count == 1:
            raise OSError("private close diagnostic")

    factory.behaviors["cpu_cores"].close_hook = close_error
    owner = inventory.MachineInventoryCollector()
    with pytest.raises(inventory.InventoryFailure, match="^inventory_cleanup_failed$"):
        owner.collect()
    assert count == 1 and len(factory.children) == 1
    assert cast(Any, owner._child) is factory.children[0]
    owner.close()
    assert count == 2
    factory.assert_closed(owner)
