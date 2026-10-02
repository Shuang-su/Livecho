"""Closed metadata contracts; approval records are evidence, never execution authority."""

from collections import Counter
from datetime import date
from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Revision = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
Nonnegative = Annotated[int, Field(ge=0)]
Positive = Annotated[int, Field(gt=0)]
Ratio = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Model = Literal["Qwen/Qwen3-ASR-1.7B", "Qwen/Qwen3-ASR-0.6B"]
Window = Literal[1, 2, 4, 6]
Condition = Literal["clean", "noise"]
Stratum = Literal["mandarin", "names", "numbers", "code_switching", "continuous"]
SpanClass = Literal["name", "number", "english"]
STRATA = ("mandarin", "names", "numbers", "code_switching", "continuous")
MODELS: tuple[Model, ...] = ("Qwen/Qwen3-ASR-1.7B", "Qwen/Qwen3-ASR-0.6B")
WINDOWS: tuple[Window, ...] = (1, 2, 4, 6)
NS = 1_000_000_000


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Approval(Closed):
    owner: Identifier
    reviewer: Identifier
    approved_on: date
    evidence_id: Identifier


class Rights(Closed):
    license_id: Identifier
    notice_ids: tuple[Identifier, ...]
    use_scope: Literal["local-preparation", "local-inference", "transient-benchmark"]
    approval: Approval


class Asset(Closed):
    path: Annotated[str, Field(min_length=1, max_length=200)]
    size: Positive
    sha256: Digest
    kind: Literal["weights", "tokenizer", "config", "notice"]

    @field_validator("path")
    @classmethod
    def safe_asset_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or str(path) != value
            or "\\" in value
            or ":" in value
            or any(part.startswith(".") for part in path.parts)
            or path.suffix not in {".safetensors", ".json", ".txt", ".model"}
        ):
            raise ValueError("asset_path_denied")
        return value


class Mirror(Closed):
    mode: Literal["huggingface", "modelscope"]
    repository: Model
    revision: Revision
    assets: tuple[Asset, ...]
    approval: Approval


class TensorRule(Closed):
    name: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.]{1,200}$")]
    source_dtype: Literal["float32", "float16", "bfloat16"]
    operation: Literal["affine-8bit-group64", "retain"]
    classification: Literal["linear", "embedding", "unsupported"]

    @model_validator(mode="after")
    def classified(self) -> Self:
        if (self.classification == "unsupported") != (self.operation == "retain"):
            raise ValueError("tensor_conversion_rule")
        return self


class PreparationManifest(Closed):
    schema_version: Literal[1] = 1
    manifest_id: Identifier
    model: Model
    source_revision: Revision
    source_assets: tuple[Asset, ...]
    source_rights: Rights
    tokenizer_rights: Rights
    conversion_rights: Rights
    converter_revision: Revision
    dependency_lock_sha256: Digest
    tensor_map: tuple[TensorRule, ...]
    mirrors: tuple[Mirror, ...]
    approval: Approval

    @model_validator(mode="after")
    def complete(self) -> Self:
        assets = {asset.path: asset for asset in self.source_assets}
        if len(assets) != len(self.source_assets) or not assets:
            raise ValueError("source_asset_inventory")
        if not {"weights", "tokenizer", "config", "notice"}.issubset(
            {asset.kind for asset in self.source_assets}
        ):
            raise ValueError("source_asset_kinds")
        if not self.tensor_map or len({rule.name for rule in self.tensor_map}) != len(
            self.tensor_map
        ):
            raise ValueError("tensor_inventory")
        if {mirror.mode for mirror in self.mirrors} != {"huggingface", "modelscope"}:
            raise ValueError("mirror_inventory")
        if len(self.mirrors) != 2:
            raise ValueError("mirror_inventory")
        for mirror in self.mirrors:
            if mirror.repository != self.model or {a.path: a for a in mirror.assets} != assets:
                raise ValueError("mirror_parity")
            if len(mirror.assets) != len(assets):
                raise ValueError("mirror_parity")
            if mirror.mode == "huggingface" and mirror.revision != self.source_revision:
                raise ValueError("canonical_revision")
        if any(
            rights.use_scope != "local-preparation"
            for rights in (self.source_rights, self.tokenizer_rights, self.conversion_rights)
        ):
            raise ValueError("preparation_rights")
        return self


class InferenceManifest(Closed):
    schema_version: Literal[1] = 1
    manifest_id: Identifier
    model: Model
    preparation_sha256: Digest
    converted_assets: tuple[Asset, ...]
    tensor_map_sha256: Digest
    provider_revision: Revision
    dependency_lock_sha256: Digest
    inference_rights: Rights
    approval: Approval

    @model_validator(mode="after")
    def complete(self) -> Self:
        if self.inference_rights.use_scope != "local-inference":
            raise ValueError("inference_rights")
        if len({a.path for a in self.converted_assets}) != len(self.converted_assets):
            raise ValueError("converted_asset_inventory")
        if not {"weights", "tokenizer", "config", "notice"}.issubset(
            {a.kind for a in self.converted_assets}
        ):
            raise ValueError("converted_asset_kinds")
        return self


def metadata_digest(record: Closed) -> str:
    """Only closed metadata models enter canonical JSON; never accepts bytes/audio."""
    import hashlib

    return hashlib.sha256(rfc8785.dumps(record.model_dump(mode="json"))).hexdigest()


class Source(Closed):
    source_id: Identifier
    publisher_id: Identifier
    speaker_id: Identifier
    consent_evidence_id: Identifier
    adult_consent: Literal[True]
    item_id: Identifier
    immutable_version: Identifier
    transient_processing: Literal[True]
    reference_retention: Literal[True]
    result_retention: Literal[True]
    reproducible_rendition: Literal[True]
    expires_on: date
    revoked: bool
    rights: Rights


class CharacterTime(Closed):
    start_ns: Nonnegative
    end_ns: Positive

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_ns <= self.start_ns or self.end_ns > 12 * NS:
            raise ValueError("reference_timing")
        return self


class Target(Closed):
    kind: SpanClass
    start: Nonnegative
    end: Positive


class Script(Closed):
    script_id: Identifier
    stratum: Stratum
    source_id: Identifier
    reference: Annotated[str, Field(min_length=30, max_length=4096)]
    duration_ns: Literal[12_000_000_000] = 12_000_000_000
    character_times: tuple[CharacterTime, ...]
    targets: tuple[Target, ...]
    noise_seed: Nonnegative

    @model_validator(mode="after")
    def annotations(self) -> Self:
        from .metrics import normalize

        reference = normalize(self.reference)
        if len(reference) < 30 or len(self.character_times) != len(reference):
            raise ValueError("reference_characters")
        previous = 0
        for timing in self.character_times:
            if timing.start_ns < previous:
                raise ValueError("reference_timing")
            if self.stratum == "continuous" and timing.start_ns - previous >= 500_000_000:
                raise ValueError("continuous_pause")
            previous = timing.end_ns
        for target in self.targets:
            if not 0 <= target.start < target.end <= len(reference):
                raise ValueError("target_range")
        required = {"names": "name", "numbers": "number", "code_switching": "english"}
        if self.stratum in required and required[self.stratum] not in {
            target.kind for target in self.targets
        }:
            raise ValueError("target_coverage")
        return self


class Corpus(Closed):
    corpus_id: Identifier
    sources: tuple[Source, ...]
    scripts: tuple[Script, ...]
    noise_algorithm: Literal["broadband-memory-v1"] = "broadband-memory-v1"
    noise_snr_db: Literal[10] = 10
    approval: Approval

    @model_validator(mode="after")
    def balanced(self) -> Self:
        from .metrics import normalize

        sources = {source.source_id: source for source in self.sources}
        if len(sources) != len(self.sources) or len({s.speaker_id for s in self.sources}) < 3:
            raise ValueError("source_speakers")
        if len({script.script_id for script in self.scripts}) != 60:
            raise ValueError("script_inventory")
        if len({normalize(script.reference) for script in self.scripts}) != 60:
            raise ValueError("distinct_scripts")
        if Counter(script.stratum for script in self.scripts) != dict.fromkeys(STRATA, 12):
            raise ValueError("stratum_inventory")
        balances: list[Counter[str]] = []
        for stratum in STRATA:
            scripts = [s for s in self.scripts if s.stratum == stratum]
            if any(s.source_id not in sources for s in scripts):
                raise ValueError("source_missing")
            counts = Counter(sources[s.source_id].speaker_id for s in scripts)
            if len(counts) < 3 or max(counts.values()) - min(counts.values()) > 1:
                raise ValueError("speaker_balance")
            balances.append(counts)
        if any(balance != balances[0] for balance in balances):
            raise ValueError("speaker_balance")
        return self

    def sources_current(self, today: date) -> bool:
        return all(
            not source.revoked
            and source.expires_on >= today
            and source.rights.use_scope == "transient-benchmark"
            for source in self.sources
        )


class Machine(Closed):
    chip: Literal["Apple M3 Ultra"]
    cpu_cores: Positive
    gpu_cores: Positive
    physical_ram_bytes: Positive
    os_build: Identifier
    power_mode: Identifier
    thermal_status: Identifier
    python_version: Identifier
    mlx_version: Identifier
    provider_version: Identifier
    converter_version: Identifier
    dependency_lock_sha256: Digest
    code_revision: Revision
    cache_state: Literal["verified-cached-weights"]
    measurement_method: Identifier


class PrivacyEvidence(Closed):
    evidence_id: Identifier
    reviewed_code_revision: Revision
    host_evidence_id: Identifier
    allocation_inventory_id: Identifier
    write_sink_observation_id: Identifier
    no_paging: Literal[True]
    no_core_dumps: Literal[True]
    no_audio_tracing: Literal[True]
    no_tensor_dumps: Literal[True]
    no_profiler_snapshots: Literal[True]
    no_media_cache: Literal[True]
    teardown_failure_injection: Literal[True]
    approval: Approval


class Settings(Closed):
    batch_size: Literal[1] = 1
    decoding: Literal["greedy"] = "greedy"
    output_token_limit: Literal[512] = 512
    silence_ns: Literal[500_000_000] = 500_000_000
    overlap_ns: Literal[800_000_000] = 800_000_000
    partial_tick_ns: Literal[250_000_000] = 250_000_000
    language_hint: None = None
    prior_prompt: None = None
    external_language_model: None = None
    forced_aligner: None = None
    quantization: Literal["affine-8bit-group64"] = "affine-8bit-group64"
