"""Closed local enroll configuration. Not community/device registration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$")
UUID4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Only loopback endpoint registry ids — never arbitrary URLs.
ALLOWED_ENDPOINT_IDS: frozenset[str] = frozenset({"loopback-local-v1"})


class WorkerConfig(BaseModel):
    """Exact closed keys only; unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    endpoint_id: str
    worker_id: str
    manifest_id: str
    host_evidence_id: str

    @field_validator("endpoint_id", "manifest_id", "host_evidence_id")
    @classmethod
    def closed_identifier(cls, value: str) -> str:
        if not IDENTIFIER.fullmatch(value):
            raise ValueError("invalid_configuration")
        return value

    @field_validator("worker_id")
    @classmethod
    def uuid4_worker(cls, value: str) -> str:
        if not UUID4.fullmatch(value):
            raise ValueError("invalid_configuration")
        return value.lower()

    @model_validator(mode="after")
    def loopback_only(self) -> Self:
        if self.endpoint_id not in ALLOWED_ENDPOINT_IDS:
            raise ValueError("invalid_configuration")
        return self


def default_config_path() -> Path:
    # Relative operator-local path; never a network location.
    return Path(".livecho") / "mlx-worker.json"


def load_config(path: Path) -> WorkerConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("invalid_configuration")
    return WorkerConfig.model_validate(raw)


def save_config(path: Path, config: WorkerConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.model_dump(mode="json"), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


class EnrollRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    endpoint_id: str = Field(default="loopback-local-v1")
    worker_id: str
    manifest_id: str
    host_evidence_id: str

    def to_config(self) -> WorkerConfig:
        return WorkerConfig(
            endpoint_id=self.endpoint_id,
            worker_id=self.worker_id,
            manifest_id=self.manifest_id,
            host_evidence_id=self.host_evidence_id,
        )
