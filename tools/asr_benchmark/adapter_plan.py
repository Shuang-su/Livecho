"""Non-executable candidate shape facts from pinned official model configuration.

This is not an inference allowlist, complete allocation inventory or MLX graph.
See the evidence source register for the exact metadata versions. Only scalar shape
facts are retained here; no upstream implementation, weights or tokenizer is copied.
"""

from dataclasses import dataclass

from .contracts import MODELS, Model
from .runtime import BlockedEvidence


@dataclass(frozen=True)
class CandidateShape:
    source_revision: str
    encoder_width: int
    encoder_layers: int
    encoder_heads: int
    decoder_width: int
    decoder_layers: int = 28
    key_value_heads: int = 8
    head_width: int = 128
    mel_channels: int = 128
    fft_size: int = 400
    hop_samples: int = 160


_CANDIDATE_FACTS: dict[Model, CandidateShape] = {
    MODELS[0]: CandidateShape("7278e1e70fe206f11671096ffdd38061171dd6e5", 1024, 24, 16, 2048),
    MODELS[1]: CandidateShape("5eb144179a02acc5e5ba31e748d22b0cf3e303b0", 896, 18, 14, 1024),
}


def candidate_shape(model: Model, source_revision: str) -> CandidateShape:
    shape = _CANDIDATE_FACTS[model]
    if source_revision != shape.source_revision:
        raise BlockedEvidence("architecture_revision_unreviewed")
    return shape


def full_decoder_cache_bytes(shape: CandidateShape, positions: int, element_bytes: int) -> int:
    """Size of a conventional full-layer K+V layout, *not* a full provider bound.

    If this optional layout is used, audio-conditioned state must be accounted for.
    A provider may use a different independently verified strategy. Success here never
    establishes privacy: input, FFT, encoder/projector/attention workspaces and copies
    are additional inventory, and their exact semantics remain to be implemented.
    """
    if type(positions) is not int or positions <= 0 or element_bytes not in (2, 4):
        raise BlockedEvidence("cache_shape")
    return (
        2
        * shape.decoder_layers
        * shape.key_value_heads
        * shape.head_width
        * positions
        * element_bytes
    )


def reject_oversized_decoder_cache(
    shape: CandidateShape,
    positions: int,
    element_bytes: int,
) -> None:
    if full_decoder_cache_bytes(shape, positions, element_bytes) > 16_777_216:
        raise BlockedEvidence("budget_exceeded")
