"""Exhaustive conversion planning from a reviewed tensor inventory; no weight loading."""

from typing import Literal

from .contracts import (
    Closed,
    InferenceManifest,
    Positive,
    PreparationManifest,
    TensorRule,
    metadata_digest,
)
from .runtime import BlockedEvidence


class TensorShape(Closed):
    rule: TensorRule
    shape: tuple[Positive, ...]


class TensorInventory(Closed):
    tensors: tuple[TensorRule, ...]


class ConversionPlan(Closed):
    preparation_sha256: str
    tensors: tuple[TensorShape, ...]
    implementation_revision: str
    dependency_lock_sha256: str
    quantization_mode: Literal["affine"] = "affine"
    bits: Literal[8] = 8
    group_size: Literal[64] = 64
    calibration_audio: Literal[False] = False


def plan_conversion(
    manifest: PreparationManifest, tensors: tuple[TensorShape, ...]
) -> ConversionPlan:
    expected = {rule.name: rule for rule in manifest.tensor_map}
    actual = {tensor.rule.name: tensor.rule for tensor in tensors}
    if expected != actual or len(actual) != len(tensors):
        raise BlockedEvidence("tensor_inventory_mismatch")
    for tensor in tensors:
        if not tensor.shape:
            raise BlockedEvidence("tensor_shape")
        if tensor.rule.operation == "affine-8bit-group64" and (
            len(tensor.shape) != 2 or tensor.shape[-1] % 64
        ):
            raise BlockedEvidence("tensor_quantization_incompatible")
    return ConversionPlan(
        preparation_sha256=metadata_digest(manifest),
        tensors=tensors,
        implementation_revision=manifest.converter_revision,
        dependency_lock_sha256=manifest.dependency_lock_sha256,
    )


def bind_inference(preparation: PreparationManifest, inference: InferenceManifest) -> None:
    if (
        inference.model != preparation.model
        or inference.preparation_sha256 != metadata_digest(preparation)
        or inference.tensor_map_sha256
        != metadata_digest(TensorInventory(tensors=preparation.tensor_map))
        or inference.dependency_lock_sha256 != preparation.dependency_lock_sha256
    ):
        raise BlockedEvidence("inference_preparation_mismatch")
