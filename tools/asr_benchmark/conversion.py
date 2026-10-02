"""Exhaustive conversion planning from a reviewed tensor inventory; no weight loading."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol, TypeVar

from .contracts import (
    Asset,
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
        or inference.source_revision != preparation.source_revision
        or inference.preparation_sha256 != metadata_digest(preparation)
        or inference.tensor_map_sha256
        != metadata_digest(TensorInventory(tensors=preparation.tensor_map))
        or inference.dependency_lock_sha256 != preparation.dependency_lock_sha256
    ):
        raise BlockedEvidence("inference_preparation_mismatch")


Tensor = TypeVar("Tensor")


class ConversionBackend(Protocol[Tensor]):
    """Reviewed model-only backend; no loader/network/audio API is exposed here."""

    def describe(self, name: str, tensor: Tensor) -> TensorShape: ...

    def quantize(
        self,
        tensor: Tensor,
        *,
        group_size: int,
        bits: int,
        mode: str,
    ) -> tuple[Tensor, Tensor, Tensor]: ...

    def evaluate(self, tensors: tuple[Tensor, ...]) -> None: ...

    def synchronize(self) -> None: ...


@dataclass(frozen=True)
class ConvertedTensor[TensorValue]:
    weight: TensorValue
    scales: TensorValue | None
    biases: TensorValue | None


def convert_verified_tensors(
    manifest: PreparationManifest,
    verified_source_assets: tuple[Asset, ...],
    tensors: Mapping[str, Tensor],
    backend: ConversionBackend[Tensor],
) -> dict[str, ConvertedTensor[Tensor]]:
    """Dispatch only an exhaustive reviewed map after model-asset verification.

    The acquisition backend must compute `verified_source_assets` from actual model
    files; an untrusted caller's digest is not verification. No backend is installed
    in the CLI. This function neither loads files nor creates an inference manifest.
    The API operations are documented by MLX; compatibility needs real tensor evidence.
    """
    if verified_source_assets != manifest.source_assets:
        raise BlockedEvidence("source_assets_unverified")
    descriptions = tuple(backend.describe(name, tensor) for name, tensor in tensors.items())
    if {item.rule.name for item in descriptions} != set(tensors):
        raise BlockedEvidence("tensor_inventory_mismatch")
    plan = plan_conversion(manifest, descriptions)
    result: dict[str, ConvertedTensor[Tensor]] = {}
    try:
        for item in plan.tensors:
            source = tensors[item.rule.name]
            if item.rule.operation == "retain":
                result[item.rule.name] = ConvertedTensor(source, None, None)
            else:
                weight, scales, biases = backend.quantize(
                    source, group_size=64, bits=8, mode="affine"
                )
                backend.evaluate((weight, scales, biases))
                backend.synchronize()
                result[item.rule.name] = ConvertedTensor(weight, scales, biases)
    except Exception:
        result.clear()
        raise BlockedEvidence("conversion_failed") from None
    return result
