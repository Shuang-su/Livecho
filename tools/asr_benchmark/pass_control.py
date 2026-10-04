"""Bounded metadata handshake; operational clocks never become benchmark measurements."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Literal, cast

from .contracts import MODELS, NS, WINDOWS, Model, Window
from .runner import PassPlan
from .runtime import BlockedEvidence

REQUEST_LIMIT = 16 * 1024
FRAME_LIMIT = 512
EVENT_LIMIT = 131072
STARTUP_NS = 5 * NS
TRANSITION_NS = 2 * NS
Phase = Literal["load", "input", "call"]


class PassFailure(BlockedEvidence):
    """An incomplete control run, never a completed/scored benchmark pass."""


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PassFailure("child_metadata_invalid")
        result[key] = value
    return result


def decode(data: bytes, limit: int) -> dict[str, object]:
    if not data or len(data) > limit or not data.endswith(b"\n"):
        raise PassFailure("child_metadata_invalid")
    try:
        value = json.loads(data, object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, RecursionError):
        raise PassFailure("child_metadata_invalid") from None
    if type(value) is not dict:
        raise PassFailure("child_metadata_invalid")
    return value


def encode(value: dict[str, object], limit: int) -> bytes:
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if len(data) > limit:
        raise PassFailure("child_metadata_limit")
    return data


def _identifier(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 96
        and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}", value) is not None
    )


def _plan(value: object) -> PassPlan:
    names = set(PassPlan.__dataclass_fields__)
    if type(value) is not dict or set(value) != names:
        raise PassFailure("pass_plan_invalid")
    scripts = value["script_ids"]
    if (
        type(scripts) not in (list, tuple)
        or len(scripts) != 60
        or not all(_identifier(item) for item in scripts)
        or tuple(scripts) != tuple(sorted(set(scripts)))
        or not _identifier(value["cold_script_id"])
        or value["cold_script_id"] != scripts[0]
        or type(value["model"]) is not str
        or value["model"] not in MODELS
        or type(value["window_seconds"]) is not int
        or value["window_seconds"] not in WINDOWS
        or type(value["repetition"]) is not int
        or value["repetition"] not in (1, 2, 3)
        or type(value["order"]) is not int
        or value["order"] not in (0, 1)
        or type(value["warmup_count"]) is not int
        or value["warmup_count"] != 3
        or type(value["conditions"]) not in (list, tuple)
        or len(value["conditions"]) != 2
        or not all(type(item) is str for item in value["conditions"])
        or tuple(value["conditions"]) != ("clean", "noise")
        or type(value["silence_duration_ns"]) is not int
        or value["silence_duration_ns"] != 60 * NS
    ):
        raise PassFailure("pass_plan_invalid")
    models = MODELS if value["repetition"] % 2 else tuple(reversed(MODELS))
    if value["model"] != models[value["order"]]:
        raise PassFailure("pass_plan_invalid")
    return PassPlan(
        cast(Model, value["model"]),
        cast(Window, value["window_seconds"]),
        value["repetition"],
        value["order"],
        scripts[0],
        3,
        tuple(scripts),
    )


@dataclass(frozen=True)
class PassRequest:
    manifest_id: str
    corpus_id: str
    plan: PassPlan
    run_id: str

    def wire(self) -> bytes:
        # Validate bounded raw fields before recursive copying/JSON allocation.
        if type(self.plan) is not PassPlan:
            raise PassFailure("pass_plan_invalid")
        validated = _plan(
            {name: getattr(self.plan, name) for name in PassPlan.__dataclass_fields__}
        )
        if (
            not _identifier(self.manifest_id)
            or not _identifier(self.corpus_id)
            or type(self.run_id) is not str
            or len(self.run_id) != 32
            or re.fullmatch(r"[0-9a-f]{32}", self.run_id) is None
        ):
            raise PassFailure("child_metadata_invalid")
        data = encode(
            {
                "version": 1,
                "manifest_id": self.manifest_id,
                "corpus_id": self.corpus_id,
                "plan": asdict(validated),
                "run_id": self.run_id,
            },
            REQUEST_LIMIT,
        )
        read_request(data)
        return data


def read_request(data: bytes) -> PassRequest:
    value = decode(data, REQUEST_LIMIT)
    if (
        set(value) != {"version", "manifest_id", "corpus_id", "plan", "run_id"}
        or type(value["version"]) is not int
        or value["version"] != 1
        or not _identifier(value["manifest_id"])
        or not _identifier(value["corpus_id"])
        or type(value["run_id"]) is not str
        or re.fullmatch(r"[0-9a-f]{32}", value["run_id"]) is None
    ):
        raise PassFailure("child_metadata_invalid")
    return PassRequest(
        str(value["manifest_id"]),
        str(value["corpus_id"]),
        _plan(value["plan"]),
        str(value["run_id"]),
    )


def request_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def event(request: PassRequest, digest: str, seq: int, kind: str, **extra: int) -> bytes:
    return encode(
        {"run_id": request.run_id, "request_sha256": digest, "seq": seq, "kind": kind, **extra},
        FRAME_LIMIT,
    )


class PassMachine:
    """Sequential permission protocol; it proves control flow, not model work."""

    def __init__(self, request: PassRequest, wire: bytes, now: int):
        self.request = request
        self.digest = request_digest(wire)
        self.state = "starting"
        self.seq = 0
        self.last_now = now
        self.deadline = now + STARTUP_NS
        self.pts = -1
        self.terminal: Literal["blocked", "control_complete"] | None = None

    def check(self, now: int) -> None:
        if type(now) is not int or now < self.last_now:
            raise PassFailure("supervisor_clock_invalid")
        self.last_now = now
        if now >= self.deadline:
            reason = {
                "load": "cached_load_timeout",
                "call": "provider_timeout",
                "input": "input_stalled",
            }.get(self.state, "child_operational_timeout")
            raise PassFailure(reason)

    def accept(self, data: bytes, now: int) -> bytes | None:
        self.check(now)
        value = decode(data, FRAME_LIMIT)
        kind = value.get("kind")
        fields = {"run_id", "request_sha256", "seq", "kind"}
        if kind == "progress":
            fields.add("pts_ns")
        if (
            set(value) != fields
            or type(kind) is not str
            or value["run_id"] != self.request.run_id
            or value["request_sha256"] != self.digest
            or type(value["seq"]) is not int
            or value["seq"] != self.seq
            or self.seq >= EVENT_LIMIT
            or self.terminal is not None
        ):
            raise PassFailure("child_metadata_invalid")
        self.seq += 1
        phase: Phase | None = None
        if self.state == "starting" and kind == "blocked":
            self.terminal = "blocked"
        elif self.state == "starting" and kind == "ready":
            phase = "load"
        elif self.state == "load" and kind == "loaded":
            self.state = "await_input"
        elif self.state in ("await_input", "after_call") and kind == "input":
            phase = "input"
            self.pts = -1
        elif self.state == "input" and kind == "progress":
            pts = value["pts_ns"]
            if type(pts) is not int or not self.pts < pts <= self.request.plan.window_seconds * NS:
                raise PassFailure("child_progress_invalid")
            self.pts = pts
            self.deadline = now + 2 * NS
            return None
        elif self.state == "input" and kind == "input_done" and self.pts >= 0:
            self.state = "await_call"
        elif self.state == "await_call" and kind == "call":
            phase = "call"
        elif self.state == "call" and kind == "called":
            self.state = "after_call"
        elif self.state == "after_call" and kind == "finished":
            self.terminal = "control_complete"
        else:
            raise PassFailure("child_phase_invalid")
        if phase is not None:
            self.state = phase
            self.deadline = now + {"load": 30, "input": 2, "call": 10}[phase] * NS
            return encode(
                {
                    "run_id": self.request.run_id,
                    "request_sha256": self.digest,
                    "seq": self.seq - 1,
                    "grant": phase,
                },
                FRAME_LIMIT,
            )
        self.deadline = now + TRANSITION_NS
        return None
