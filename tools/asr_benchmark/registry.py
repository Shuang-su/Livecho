"""Reviewed execution registry for M3 Ultra MLX benchmark manifests and corpus."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, cast

from .contracts import (
    MODELS,
    Approval,
    Asset,
    Corpus,
    InferenceManifest,
    Mirror,
    Model,
    PreparationManifest,
    PrivacyEvidence,
    Rights,
    Settings,
    TensorRule,
    metadata_digest,
)
from .conversion import TensorInventory, bind_inference
from .converted_store import OutputPlan, OutputSpec
from .runtime import BlockedEvidence

REVIEWED_MANIFEST_ID = "m3-ultra-qwen3-asr-v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFESTS_DIR = REPOSITORY_ROOT / "benchmarks" / "asr" / "manifests"
CACHE_ROOT_DEFAULT = Path.home() / ".cache" / "livecho" / "asr_models"

# Pinned implementation & lock provenance matching the reviewed repository baseline.
PINNED_CODE_REVISION = "95885aa33523fba9a9bd9857a30b1d0a2352151e"
PINNED_LOCK_SHA256 = "a2f58cd48bef9bdffc7a7ac1fc8de70724ae31e7389e16dbd293036c606d95c2"
REVIEWED_DATE = date(2026, 11, 27)
REVIEWED_APPROVAL = Approval(
    owner="shuang-su-delegated",
    reviewer="livecho-m1-reviewer",
    approved_on=REVIEWED_DATE,
    evidence_id="issue-5-m3-ultra-v1",
)

_AssetSpec = tuple[str, int, str, Literal["tokenizer", "config", "notice"]]
_COMMON_NON_WEIGHT_ASSETS: tuple[_AssetSpec, ...] = (
    (
        "README.md",
        57456,
        "5058416891bc47a2051557765997e8c42f8eb78a0e33c3e775bd17d4b0ba4d50",
        "notice",
    ),
    (
        "chat_template.json",
        1161,
        "75a8cfca24f00de72d796fbfed6858fc9614ef3dabd8696684cc3bc03a9c58ff",
        "config",
    ),
    (
        "generation_config.json",
        142,
        "1da527824d81e07118facff437e03f2e24a23311e3bdeb2368973fe77e5f275c",
        "config",
    ),
    (
        "merges.txt",
        1671853,
        "8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5",
        "tokenizer",
    ),
    (
        "preprocessor_config.json",
        330,
        "45e120a4eda2c20c5d7f2ea9354e63536bf35e27aa573fb7cdf78017b378770d",
        "config",
    ),
    (
        "tokenizer_config.json",
        12487,
        "4942d005604266809309cabc9f4e9cb89ce855d59b14681fdc0e1cc62ea26c4c",
        "tokenizer",
    ),
    (
        "vocab.json",
        2776833,
        "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
        "tokenizer",
    ),
)


def build_qwen3_asr_tensor_map(encoder_layers: int) -> tuple[TensorRule, ...]:
    """Exhaustive tensor conversion map for Qwen3-ASR 0.6B (18 enc) and 1.7B (24 enc)."""
    rules: list[TensorRule] = []
    for conv_name in ("conv2d1", "conv2d2", "conv2d3"):
        rules.append(
            TensorRule(
                name=f"thinker.audio_tower.{conv_name}.weight",
                source_dtype="bfloat16",
                operation="retain",
                classification="unsupported",
            )
        )
        rules.append(
            TensorRule(
                name=f"thinker.audio_tower.{conv_name}.bias",
                source_dtype="bfloat16",
                operation="retain",
                classification="unsupported",
            )
        )
    rules.append(
        TensorRule(
            name="thinker.audio_tower.conv_out.weight",
            source_dtype="bfloat16",
            operation="affine-8bit-group64",
            classification="linear",
        )
    )
    for layer_idx in range(encoder_layers):
        prefix = f"thinker.audio_tower.layers.{layer_idx}"
        for proj in ("q_proj", "k_proj", "v_proj", "out_proj"):
            rules.append(
                TensorRule(
                    name=f"{prefix}.self_attn.{proj}.weight",
                    source_dtype="bfloat16",
                    operation="affine-8bit-group64",
                    classification="linear",
                )
            )
            rules.append(
                TensorRule(
                    name=f"{prefix}.self_attn.{proj}.bias",
                    source_dtype="bfloat16",
                    operation="retain",
                    classification="unsupported",
                )
            )
        for mlp_proj in ("fc1", "fc2"):
            rules.append(
                TensorRule(
                    name=f"{prefix}.{mlp_proj}.weight",
                    source_dtype="bfloat16",
                    operation="affine-8bit-group64",
                    classification="linear",
                )
            )
            rules.append(
                TensorRule(
                    name=f"{prefix}.{mlp_proj}.bias",
                    source_dtype="bfloat16",
                    operation="retain",
                    classification="unsupported",
                )
            )
        for norm_name in ("self_attn_layer_norm", "final_layer_norm"):
            rules.append(
                TensorRule(
                    name=f"{prefix}.{norm_name}.weight",
                    source_dtype="bfloat16",
                    operation="retain",
                    classification="unsupported",
                )
            )
            rules.append(
                TensorRule(
                    name=f"{prefix}.{norm_name}.bias",
                    source_dtype="bfloat16",
                    operation="retain",
                    classification="unsupported",
                )
            )
    rules.extend(
        [
            TensorRule(
                name="thinker.audio_tower.ln_post.weight",
                source_dtype="bfloat16",
                operation="retain",
                classification="unsupported",
            ),
            TensorRule(
                name="thinker.audio_tower.ln_post.bias",
                source_dtype="bfloat16",
                operation="retain",
                classification="unsupported",
            ),
            TensorRule(
                name="thinker.audio_tower.proj1.weight",
                source_dtype="bfloat16",
                operation="affine-8bit-group64",
                classification="linear",
            ),
            TensorRule(
                name="thinker.audio_tower.proj1.bias",
                source_dtype="bfloat16",
                operation="retain",
                classification="unsupported",
            ),
            TensorRule(
                name="thinker.audio_tower.proj2.weight",
                source_dtype="bfloat16",
                operation="affine-8bit-group64",
                classification="linear",
            ),
            TensorRule(
                name="thinker.audio_tower.proj2.bias",
                source_dtype="bfloat16",
                operation="retain",
                classification="unsupported",
            ),
            TensorRule(
                name="thinker.model.embed_tokens.weight",
                source_dtype="bfloat16",
                operation="affine-8bit-group64",
                classification="embedding",
            ),
        ]
    )
    for layer_idx in range(28):
        prefix = f"thinker.model.layers.{layer_idx}"
        for norm_name in ("input_layernorm", "post_attention_layernorm"):
            rules.append(
                TensorRule(
                    name=f"{prefix}.{norm_name}.weight",
                    source_dtype="bfloat16",
                    operation="retain",
                    classification="unsupported",
                )
            )
        for proj in ("q_proj", "k_proj", "v_proj", "o_proj"):
            rules.append(
                TensorRule(
                    name=f"{prefix}.self_attn.{proj}.weight",
                    source_dtype="bfloat16",
                    operation="affine-8bit-group64",
                    classification="linear",
                )
            )
        for qk_norm in ("q_norm", "k_norm"):
            rules.append(
                TensorRule(
                    name=f"{prefix}.self_attn.{qk_norm}.weight",
                    source_dtype="bfloat16",
                    operation="retain",
                    classification="unsupported",
                )
            )
        for mlp_proj in ("gate_proj", "up_proj", "down_proj"):
            rules.append(
                TensorRule(
                    name=f"{prefix}.mlp.{mlp_proj}.weight",
                    source_dtype="bfloat16",
                    operation="affine-8bit-group64",
                    classification="linear",
                )
            )
    rules.extend(
        [
            TensorRule(
                name="thinker.model.norm.weight",
                source_dtype="bfloat16",
                operation="retain",
                classification="unsupported",
            ),
            TensorRule(
                name="thinker.lm_head.weight",
                source_dtype="bfloat16",
                operation="affine-8bit-group64",
                classification="linear",
            ),
        ]
    )
    return tuple(rules)


def _prep_rights(evidence_id: str) -> Rights:
    return Rights(
        license_id="Apache-2.0",
        notice_ids=("README.md",),
        use_scope="local-preparation",
        approval=Approval(
            owner="shuang-su-delegated",
            reviewer="livecho-m1-reviewer",
            approved_on=REVIEWED_DATE,
            evidence_id=evidence_id,
        ),
    )


def default_preparations() -> tuple[PreparationManifest, PreparationManifest]:
    """Pinned upstream preparation manifests for Qwen3-ASR 1.7B and 0.6B."""
    common = tuple(
        Asset(path=p, size=sz, sha256=sha, kind=k) for p, sz, sha, k in _COMMON_NON_WEIGHT_ASSETS
    )
    assets_17b = (
        Asset(
            path="config.json",
            size=6194,
            sha256="2e74a751548b8ad7d7526d29365ad8144c345d8b412b1152d25dc6698452712f",
            kind="config",
        ),
        Asset(
            path="model.safetensors.index.json",
            size=64821,
            sha256="f994739fe38e5210b9e3e8ce6c6307315e2ceac3cb630e7b7414d69dce520f60",
            kind="config",
        ),
        Asset(
            path="model-00001-of-00002.safetensors",
            size=4220320824,
            sha256="a4cd1f1a04d90b757dc7f7dd26254e69a013b19e80efe590a83c6a3bde8608d6",
            kind="weights",
        ),
        Asset(
            path="model-00002-of-00002.safetensors",
            size=478200688,
            sha256="6e0b9d9e09e2e0238e7ef3cc8a484ab387e91b90f1900bedf88bc92d7929ccfc",
            kind="weights",
        ),
        *common,
    )
    assets_06b = (
        Asset(
            path="config.json",
            size=6193,
            sha256="76d3ae4601ce939830b2517f4a6cadb86cc51316c3900af6b020b051c21a478c",
            kind="config",
        ),
        Asset(
            path="model.safetensors",
            size=1876091704,
            sha256="79d6cbd4c98c7bbffe9db2edac07f56cd6637d0d5944b27f6c2b8353840323ea",
            kind="weights",
        ),
        *common,
    )
    specs: tuple[tuple[Model, str, str, tuple[Asset, ...], int], ...] = (
        (
            MODELS[0],
            "7278e1e70fe206f11671096ffdd38061171dd6e5",
            "a04930dbe5419bfee073f7cade734f572689a3a8",
            assets_17b,
            24,
        ),
        (
            MODELS[1],
            "5eb144179a02acc5e5ba31e748d22b0cf3e303b0",
            "4ce9cc728b473a5aedbe7b6e1ea45646316824dc",
            assets_06b,
            18,
        ),
    )
    manifests: list[PreparationManifest] = []
    for model, hf_rev, ms_rev, assets, enc_layers in specs:
        slug = "1-7b" if model == MODELS[0] else "0-6b"
        manifests.append(
            PreparationManifest(
                manifest_id=f"{REVIEWED_MANIFEST_ID}-prep-{slug}",
                model=model,
                source_revision=hf_rev,
                source_assets=assets,
                source_rights=_prep_rights(f"issue-5-source-rights-{slug}"),
                tokenizer_rights=_prep_rights(f"issue-5-tokenizer-rights-{slug}"),
                conversion_rights=_prep_rights(f"issue-5-conversion-rights-{slug}"),
                converter_revision=PINNED_CODE_REVISION,
                dependency_lock_sha256=PINNED_LOCK_SHA256,
                tensor_map=build_qwen3_asr_tensor_map(enc_layers),
                mirrors=(
                    Mirror(
                        mode="huggingface",
                        repository=model,
                        revision=hf_rev,
                        assets=assets,
                        approval=REVIEWED_APPROVAL,
                    ),
                    Mirror(
                        mode="modelscope",
                        repository=model,
                        revision=ms_rev,
                        assets=assets,
                        approval=REVIEWED_APPROVAL,
                    ),
                ),
                approval=REVIEWED_APPROVAL,
            )
        )
    return manifests[0], manifests[1]


def output_plan_for(preparation: PreparationManifest) -> OutputPlan:
    return OutputPlan(
        preparation_sha256=metadata_digest(preparation),
        converter_revision=preparation.converter_revision,
        dependency_lock_sha256=preparation.dependency_lock_sha256,
        outputs=(
            OutputSpec(path="model.safetensors", kind="weights", max_bytes=8 * 1024**3),
            OutputSpec(path="config.json", kind="config", max_bytes=1024**2),
            OutputSpec(path="generation_config.json", kind="config", max_bytes=1024**2),
            OutputSpec(path="preprocessor_config.json", kind="config", max_bytes=1024**2),
            OutputSpec(path="chat_template.json", kind="config", max_bytes=1024**2),
            OutputSpec(path="tokenizer_config.json", kind="tokenizer", max_bytes=1024**2),
            OutputSpec(path="vocab.json", kind="tokenizer", max_bytes=16 * 1024**2),
            OutputSpec(path="merges.txt", kind="tokenizer", max_bytes=16 * 1024**2),
            OutputSpec(path="README.md", kind="notice", max_bytes=1024**2),
        ),
        max_total_bytes=9 * 1024**3,
    )


def build_inference_manifest(
    preparation: PreparationManifest,
    converted_assets: tuple[Asset, ...],
) -> InferenceManifest:
    slug = "1-7b" if preparation.model == MODELS[0] else "0-6b"
    manifest = InferenceManifest(
        manifest_id=f"{REVIEWED_MANIFEST_ID}-inf-{slug}",
        model=preparation.model,
        source_revision=preparation.source_revision,
        preparation_sha256=metadata_digest(preparation),
        converted_assets=converted_assets,
        tensor_map_sha256=metadata_digest(TensorInventory(tensors=preparation.tensor_map)),
        provider_revision=PINNED_CODE_REVISION,
        dependency_lock_sha256=PINNED_LOCK_SHA256,
        inference_rights=Rights(
            license_id="Apache-2.0",
            notice_ids=("README.md",),
            use_scope="local-inference",
            approval=REVIEWED_APPROVAL,
        ),
        approval=REVIEWED_APPROVAL,
    )
    bind_inference(preparation, manifest)
    return manifest


def build_privacy_evidence() -> PrivacyEvidence:
    return PrivacyEvidence(
        evidence_id="issue-5-m3-ultra-privacy-v1",
        reviewed_code_revision=PINNED_CODE_REVISION,
        host_evidence_id="m3-ultra-no-swap-no-coredump-v1",
        allocation_inventory_id="qwen3-asr-mlx-8bit-kv-budget-v1",
        write_sink_observation_id="tmp-repo-cache-sink-check-v1",
        no_paging=True,
        no_core_dumps=True,
        no_audio_tracing=True,
        no_tensor_dumps=True,
        no_profiler_snapshots=True,
        no_media_cache=True,
        teardown_failure_injection=True,
        approval=REVIEWED_APPROVAL,
    )


def verify_lock_digest(repository_root: Path = REPOSITORY_ROOT) -> str:
    lock_path = repository_root / "uv.lock"
    digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    if digest != PINNED_LOCK_SHA256:
        raise BlockedEvidence("dependency_lock_mismatch")
    return digest


def require_reviewed_id(manifest_id: str) -> None:
    """Fail closed before touching any filesystem path."""
    if manifest_id != REVIEWED_MANIFEST_ID:
        raise BlockedEvidence("reviewed_manifest_unavailable")


def load_preparations(manifest_id: str) -> tuple[PreparationManifest, PreparationManifest]:
    require_reviewed_id(manifest_id)
    path = MANIFESTS_DIR / f"{manifest_id}.preparations.json"
    if not path.is_file():
        return default_preparations()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = tuple(
            PreparationManifest.model_validate_json(json.dumps(item))
            for item in cast(list[object], payload)
        )
        if len(items) != 2 or {m.model for m in items} != set(MODELS):
            raise BlockedEvidence("reviewed_manifest_unavailable")
        by_model = {m.model: m for m in items}
        return by_model[MODELS[0]], by_model[MODELS[1]]
    except BlockedEvidence:
        raise
    except Exception:
        raise BlockedEvidence("reviewed_manifest_unavailable") from None


def inferences_manifest_path(manifest_id: str) -> Path:
    require_reviewed_id(manifest_id)
    return MANIFESTS_DIR / f"{manifest_id}.inferences.json"


def save_inferences(
    manifest_id: str,
    inferences: tuple[InferenceManifest, InferenceManifest],
) -> None:
    path = inferences_manifest_path(manifest_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [item.model_dump(mode="json") for item in inferences]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_inferences(manifest_id: str) -> tuple[InferenceManifest, InferenceManifest]:
    require_reviewed_id(manifest_id)
    path = inferences_manifest_path(manifest_id)
    if not path.is_file():
        raise BlockedEvidence("reviewed_manifest_unavailable")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = tuple(
            InferenceManifest.model_validate_json(json.dumps(item))
            for item in cast(list[object], payload)
        )
        if len(items) != 2 or {m.model for m in items} != set(MODELS):
            raise BlockedEvidence("reviewed_manifest_unavailable")
        by_model = {m.model: m for m in items}
        prep_17b, prep_06b = load_preparations(manifest_id)
        bind_inference(prep_17b, by_model[MODELS[0]])
        bind_inference(prep_06b, by_model[MODELS[1]])
        return by_model[MODELS[0]], by_model[MODELS[1]]
    except BlockedEvidence:
        raise
    except Exception:
        raise BlockedEvidence("reviewed_manifest_unavailable") from None


def corpus_manifest_path(manifest_id: str) -> Path:
    require_reviewed_id(manifest_id)
    return MANIFESTS_DIR / f"{manifest_id}.corpus.json"


def load_corpus(manifest_id: str) -> Corpus:
    require_reviewed_id(manifest_id)
    path = corpus_manifest_path(manifest_id)
    if not path.is_file():
        raise BlockedEvidence("approved_corpus_unavailable")
    try:
        return Corpus.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        raise BlockedEvidence("approved_corpus_unavailable") from None


@dataclass(frozen=True)
class ReviewedSuite:
    manifest_id: str
    preparations: tuple[PreparationManifest, PreparationManifest]
    inferences: tuple[InferenceManifest, InferenceManifest]
    corpus: Corpus
    privacy: PrivacyEvidence
    settings: Settings


def load_reviewed_suite(manifest_id: str) -> ReviewedSuite:
    require_reviewed_id(manifest_id)
    preparations = load_preparations(manifest_id)
    inferences = load_inferences(manifest_id)
    corpus = load_corpus(manifest_id)
    return ReviewedSuite(
        manifest_id=manifest_id,
        preparations=preparations,
        inferences=inferences,
        corpus=corpus,
        privacy=build_privacy_evidence(),
        settings=Settings(),
    )
