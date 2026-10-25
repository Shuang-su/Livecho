from io import StringIO

import pytest
from livecho_protocol.models import ModelManifestRefV1

from tools.asr_benchmark.adapter_plan import (
    candidate_shape,
    full_decoder_cache_bytes,
    reject_oversized_decoder_cache,
)
from tools.asr_benchmark.contracts import MODELS, metadata_digest, protocol_projection
from tools.asr_benchmark.conversion import TensorShape, convert_verified_tensors
from tools.asr_benchmark.runtime import BlockedEvidence
from tools.asr_benchmark.serialization import (
    parse_report,
    run_identity,
    serialize_report,
    write_report,
)

from .factories import inference, preparation, report


def test_projection_is_exact_existing_protocol_tuple_and_full_manifest_digest() -> None:
    manifest = inference(MODELS[0])
    projection = protocol_projection(manifest)
    parsed = ModelManifestRefV1.model_validate(projection.model_dump())
    assert set(projection.model_dump()) == {"provider", "model_id", "revision", "sha256"}
    assert parsed.sha256 == metadata_digest(manifest)
    assert parsed.revision == manifest.source_revision
    changed = manifest.model_copy(update={"provider_revision": "f" * 40})
    assert protocol_projection(changed).sha256 != parsed.sha256


def test_report_roundtrip_unknown_audio_fields_and_frozen_identity() -> None:
    # An incomplete report is sufficient for serialization; it cannot qualify.
    source = report().model_copy(update={"repetitions": (), "interrupted": True})
    frozen = run_identity(source)
    text = serialize_report(source, frozen)
    assert parse_report(text, frozen) == source
    sink = StringIO()
    write_report(source, frozen, sink)
    assert sink.getvalue() == text
    with pytest.raises(BlockedEvidence, match="report_invalid"):
        parse_report('{"audio":"forbidden-extra",' + text[1:], frozen)
    changed = source.model_copy(update={"run_id": "different-run"})
    with pytest.raises(BlockedEvidence, match="frozen_run_changed"):
        serialize_report(changed, frozen)
    machine = source.machine.model_copy(update={"power_mode": "different-mode"})
    with pytest.raises(BlockedEvidence, match="frozen_run_changed"):
        serialize_report(source.model_copy(update={"machine": machine}), frozen)


def test_conversion_calls_only_the_exact_affine_interface_and_synchronizes() -> None:
    manifest = preparation()
    name = manifest.tensor_map[0].name
    calls: list[str] = []

    class MetadataBackend:
        def describe(self, name: str, tensor: str) -> TensorShape:
            assert tensor == "metadata-handle"
            return TensorShape(rule=manifest.tensor_map[0], shape=(128, 64))

        def quantize(
            self,
            tensor: str,
            *,
            group_size: int,
            bits: int,
            mode: str,
        ) -> tuple[str, str, str]:
            assert (group_size, bits, mode) == (64, 8, "affine")
            calls.append("quantize")
            return ("packed-metadata", "scale-metadata", "bias-metadata")

        def evaluate(self, tensors: tuple[str, ...]) -> None:
            assert len(tensors) == 3
            calls.append("evaluate")

        def synchronize(self) -> None:
            calls.append("synchronize")

    backend = MetadataBackend()
    result = convert_verified_tensors(
        manifest, manifest.source_assets, {name: "metadata-handle"}, backend
    )
    assert calls == ["quantize", "evaluate", "synchronize"]
    assert result[name].scales == "scale-metadata"
    with pytest.raises(BlockedEvidence, match="source_assets_unverified"):
        convert_verified_tensors(manifest, (), {name: "metadata-handle"}, backend)
    assert calls == ["quantize", "evaluate", "synchronize"]


def test_pinned_candidate_shapes_are_not_a_blanket_mlx_or_memory_approval() -> None:
    large = candidate_shape(MODELS[0], "7278e1e70fe206f11671096ffdd38061171dd6e5")
    small = candidate_shape(MODELS[1], "5eb144179a02acc5e5ba31e748d22b0cf3e303b0")
    assert (large.encoder_width, small.encoder_width) == (1024, 896)
    assert full_decoder_cache_bytes(large, 512, 2) == 58_720_256
    assert full_decoder_cache_bytes(small, 512, 2) == 58_720_256
    with pytest.raises(BlockedEvidence, match="budget_exceeded"):
        reject_oversized_decoder_cache(large, 512, 2)
    with pytest.raises(BlockedEvidence, match="revision_unreviewed"):
        candidate_shape(MODELS[0], "f" * 40)
