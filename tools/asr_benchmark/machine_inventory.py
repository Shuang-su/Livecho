"""Fixed, partial machine observations. Never a Machine or host-privacy approval."""

import os
import platform
import re
import selectors
import subprocess
import sys
import time
from collections.abc import Callable
from types import MappingProxyType
from typing import Annotated, Literal, Self, get_args

from pydantic import ConfigDict, Field, model_validator

from .contracts import NS, Closed, Machine
from .runtime import BlockedEvidence

ObservedField = Literal["cpu_cores", "physical_ram_bytes", "os_build", "python_version"]
QueryField = Literal["cpu_cores", "physical_ram_bytes", "os_build"]
MachineField = Literal[
    "chip",
    "cpu_cores",
    "gpu_cores",
    "physical_ram_bytes",
    "os_build",
    "power_mode",
    "thermal_status",
    "python_version",
    "mlx_version",
    "provider_version",
    "converter_version",
    "provider_revision",
    "converter_revision",
    "dependency_lock_sha256",
    "code_revision",
    "cache_state",
    "measurement_method",
]
MissingReason = Literal[
    "not_collected",
    "platform_unsupported",
    "query_unavailable",
    "query_failed",
    "query_timeout",
    "collection_timeout",
    "output_invalid",
    "python_unavailable",
]
_COMMANDS = MappingProxyType(
    {
        "cpu_cores": ("/usr/sbin/sysctl", "-n", "hw.physicalcpu_max"),
        "physical_ram_bytes": ("/usr/sbin/sysctl", "-n", "hw.memsize"),
        "os_build": ("/usr/bin/sw_vers", "--buildVersion"),
    }
)
_OUTPUT_LIMIT = 128
_QUERY_NS = 2 * NS
_COLLECTION_NS = 6 * NS
_TERM_SECONDS = 1.0
_REAP_SECONDS = 1.0
_BUILD = r"[1-9][0-9]{0,2}[A-Z][0-9]{1,6}[a-z]?"
_PYTHON = r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,3}(?:(?:a|b|rc)[0-9]{1,3})?"


class InventoryFailure(BlockedEvidence):
    """Stable cancellation/ownership failure; no snapshot is delivered."""


class _Missing(Exception):
    def __init__(self, reason: MissingReason):
        self.reason = reason


class _InventoryClosed(Closed):
    model_config = ConfigDict(revalidate_instances="always")


class InventoryObservations(_InventoryClosed):
    cpu_cores: Annotated[int, Field(gt=0, le=4096)] | None = None
    physical_ram_bytes: Annotated[int, Field(gt=0, le=2**60)] | None = None
    os_build: Annotated[str, Field(pattern=f"^{_BUILD}$", max_length=16)] | None = None
    python_version: Annotated[str, Field(pattern=f"^{_PYTHON}$", max_length=32)] | None = None


class InventorySources(_InventoryClosed):
    cpu_cores: Literal["sysctl-hw.physicalcpu_max"] = "sysctl-hw.physicalcpu_max"
    physical_ram_bytes: Literal["sysctl-hw.memsize"] = "sysctl-hw.memsize"
    os_build: Literal["sw_vers-buildVersion"] = "sw_vers-buildVersion"
    python_version: Literal["platform.python_version"] = "platform.python_version"


class MissingField(_InventoryClosed):
    field: MachineField
    reason: MissingReason


class InventorySnapshot(_InventoryClosed):
    schema_version: Literal[1] = 1
    state: Literal["incomplete"] = "incomplete"
    collection_method: Literal["fixed-local-queries-v1"] = "fixed-local-queries-v1"
    started_ns: Annotated[int, Field(ge=0)]
    finished_ns: Annotated[int, Field(ge=0)]
    observations: InventoryObservations
    sources: InventorySources = InventorySources()
    missing: Annotated[tuple[MissingField, ...], Field(max_length=17)]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.finished_ns < self.started_ns:
            raise ValueError("inventory_clock_invalid")
        observed = self.observations.model_dump()
        expected = tuple(name for name in Machine.model_fields if observed.get(name) is None)
        if tuple(item.field for item in self.missing) != expected:
            raise ValueError("inventory_missing_fields")
        for item in self.missing:
            if (item.field not in observed) != (item.reason == "not_collected"):
                raise ValueError("inventory_missing_reason")
        return self


def _spawn(field: QueryField) -> subprocess.Popen[bytes]:
    if type(field) is not str or field not in _COMMANDS:
        raise InventoryFailure("inventory_query_invalid")
    return subprocess.Popen(
        _COMMANDS[field],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=False,
        env={},
        cwd="/",
        close_fds=True,
        bufsize=0,
    )


def _parse(field: QueryField, raw: bytes) -> int | str:
    if type(raw) is not bytes or not 1 <= len(raw) <= _OUTPUT_LIMIT or not raw.endswith(b"\n"):
        raise _Missing("output_invalid")
    try:
        value = raw[:-1].decode("ascii")
    except UnicodeError:
        raise _Missing("output_invalid") from None
    if field == "os_build":
        if re.fullmatch(_BUILD, value) is None:
            raise _Missing("output_invalid")
        return value
    if re.fullmatch(r"[1-9][0-9]{0,18}", value) is None:
        raise _Missing("output_invalid")
    number = int(value)
    cap = 4096 if field == "cpu_cores" else 2**60
    if number > cap:
        raise _Missing("output_invalid")
    return number


class MachineInventoryCollector:
    """Synchronous single-use owner; only an explicit close may retry failed cleanup."""

    def __init__(self) -> None:
        self._used = False
        self._child: subprocess.Popen[bytes] | None = None
        self._last_now = 0

    def _now(self) -> int:
        try:
            now = time.monotonic_ns()
        except Exception:
            raise InventoryFailure("inventory_clock_invalid") from None
        if type(now) is not int or now < self._last_now:
            raise InventoryFailure("inventory_clock_invalid")
        self._last_now = now
        return now

    @staticmethod
    def _cancel(cancelled: Callable[[], bool]) -> None:
        try:
            value = cancelled()
        except Exception:
            raise InventoryFailure("inventory_callback_failed") from None
        if type(value) is not bool:
            raise InventoryFailure("inventory_callback_failed")
        if value:
            raise InventoryFailure("cancelled")

    def _check(self, deadline: int, cancelled: Callable[[], bool]) -> int:
        self._cancel(cancelled)
        now = self._now()
        if now >= deadline:
            raise _Missing("query_timeout")
        return now

    def close(self) -> None:
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
            try:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=_REAP_SECONDS)
            except BaseException:
                pass
        finally:
            if child.stdout is not None:
                try:
                    child.stdout.close()
                except BaseException:
                    failed = True
        if failed:
            raise InventoryFailure("inventory_cleanup_failed") from None
        self._child = None

    def _query(
        self,
        field: QueryField,
        deadline: int,
        cancelled: Callable[[], bool],
    ) -> int | str:
        raw = bytearray()
        try:
            self._check(deadline, cancelled)
            self._child = _spawn(field)
            self._check(deadline, cancelled)
            child = self._child
            assert child.stdout is not None
            os.set_blocking(child.stdout.fileno(), False)
            eof = False
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                while True:
                    now = self._check(deadline, cancelled)
                    code = child.poll()
                    if code is not None and code != 0:
                        raise _Missing("query_failed")
                    if eof and code is not None:
                        child.wait(timeout=_REAP_SECONDS)
                        break
                    ready = selector.select(min(0.02, (deadline - now) / NS))
                    for _ in ready:
                        self._check(deadline, cancelled)
                        try:
                            data = os.read(child.stdout.fileno(), _OUTPUT_LIMIT + 1 - len(raw))
                        except BlockingIOError:
                            continue
                        if not data:
                            eof = True
                            selector.unregister(child.stdout)
                        else:
                            raw.extend(data)
                            if len(raw) > _OUTPUT_LIMIT:
                                raise _Missing("output_invalid")
        except FileNotFoundError:
            raise _Missing("query_unavailable") from None
        except (OSError, ValueError):
            raise _Missing("query_failed") from None
        finally:
            self.close()
        self._check(deadline, cancelled)
        result = _parse(field, bytes(raw))
        self._check(deadline, cancelled)
        return result

    def collect(self, *, cancelled: Callable[[], bool] = lambda: False) -> InventorySnapshot:
        if self._used:
            raise InventoryFailure("inventory_owner_used")
        self._used = True
        started = self._now()
        deadline = started + _COLLECTION_NS
        values: dict[str, int | str] = {}
        reasons: dict[str, MissingReason] = {}
        try:
            self._check(deadline, cancelled)
            try:
                version = platform.python_version()
            except Exception:
                raise _Missing("python_unavailable") from None
            self._check(deadline, cancelled)
            if (
                type(version) is not str
                or len(version) > 32
                or re.fullmatch(_PYTHON, version) is None
            ):
                raise _Missing("output_invalid")
            values["python_version"] = version
        except _Missing as missing:
            reasons["python_version"] = (
                "collection_timeout" if missing.reason == "query_timeout" else missing.reason
            )
        for field in get_args(QueryField):
            self._cancel(cancelled)
            now = self._now()
            if now >= deadline:
                reasons[field] = "collection_timeout"
            elif sys.platform != "darwin":
                reasons[field] = "platform_unsupported"
            else:
                try:
                    # _query owns its entire child lifetime, including every failure.
                    # Do not silently retry a failed cleanup from an outer finally.
                    values[field] = self._query(field, min(now + _QUERY_NS, deadline), cancelled)
                except _Missing as missing:
                    reasons[field] = missing.reason
        self._cancel(cancelled)
        finished = self._now()
        missing_fields = tuple(
            MissingField(field=field, reason=reasons.get(field, "not_collected"))
            for field in get_args(MachineField)
            if field not in values
        )
        return InventorySnapshot(
            started_ns=started,
            finished_ns=finished,
            observations=InventoryObservations.model_validate(values),
            missing=missing_fields,
        )
