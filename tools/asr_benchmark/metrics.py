"""Deterministic Unicode text metrics; no audio or hypotheses are persisted here."""

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal


def normalize(text: str) -> str:
    return "".join(
        chr(ord(char) + 32) if "A" <= char <= "Z" else char
        for char in unicodedata.normalize("NFC", text)
        if not char.isspace() and not unicodedata.category(char).startswith("P")
    )


@dataclass(frozen=True)
class Edit:
    kind: Literal["match", "substitution", "deletion", "insertion"]
    reference_index: int
    hypothesis_index: int
    reference: str
    hypothesis: str


def align(reference: str, hypothesis: str) -> tuple[Edit, ...]:
    """Suffix DP permits forward tie order: match, substitution, deletion, insertion."""
    reference, hypothesis = normalize(reference), normalize(hypothesis)
    if max(len(reference), len(hypothesis)) > 4096:
        raise ValueError("text_limit")
    n, m = len(reference), len(hypothesis)
    costs = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            if i == n:
                costs[i][j] = m - j
            elif j == m:
                costs[i][j] = n - i
            else:
                costs[i][j] = min(
                    costs[i + 1][j + 1] + (reference[i] != hypothesis[j]),
                    costs[i + 1][j] + 1,
                    costs[i][j + 1] + 1,
                )
    result: list[Edit] = []
    i = j = 0
    while i < n or j < m:
        if i < n and j < m and costs[i][j] == costs[i + 1][j + 1] + (reference[i] != hypothesis[j]):
            kind: Literal["match", "substitution"] = (
                "match" if reference[i] == hypothesis[j] else "substitution"
            )
            result.append(Edit(kind, i, j, reference[i], hypothesis[j]))
            i += 1
            j += 1
        elif i < n and costs[i][j] == 1 + costs[i + 1][j]:
            result.append(Edit("deletion", i, j, reference[i], ""))
            i += 1
        else:
            result.append(Edit("insertion", i, j, "", hypothesis[j]))
            j += 1
    return tuple(result)


@dataclass(frozen=True)
class ErrorCounts:
    substitutions: int
    deletions: int
    insertions: int
    reference_characters: int

    @property
    def cer(self) -> float | None:
        if not self.reference_characters:
            return None
        return (self.substitutions + self.deletions + self.insertions) / self.reference_characters


def error_counts(reference: str, hypothesis: str) -> ErrorCounts:
    edits = align(reference, hypothesis)
    return ErrorCounts(
        sum(edit.kind == "substitution" for edit in edits),
        sum(edit.kind == "deletion" for edit in edits),
        sum(edit.kind == "insertion" for edit in edits),
        len(normalize(reference)),
    )


def target_exact(edits: Sequence[Edit], start: int, end: int) -> bool:
    if not 0 <= start < end:
        raise ValueError("target_range")
    selected = [edit for edit in edits if start <= edit.reference_index < end]
    return sum(edit.kind == "match" for edit in selected) == end - start and all(
        edit.kind == "match" for edit in selected
    )


def stitch(parts: Sequence[str]) -> str:
    merged = ""
    for part in parts:
        normalized = normalize(part)
        bound = min(32, len(merged), len(normalized))
        overlap = next(
            (size for size in range(bound, 0, -1) if merged[-size:] == normalized[:size]), 0
        )
        merged += normalized[overlap:]
    return merged


@dataclass(frozen=True)
class BoundaryCounts:
    duplicates: int
    omissions: int
    reference_characters: int


def boundary_counts(
    reference: str, hypothesis: str, intervals: Sequence[tuple[int, int]]
) -> BoundaryCounts:
    """Count each boundary's shared interval, including insertion at its right edge.

    Boundaries are disjoint reference character ranges for the scored stream. An
    insertion must both align locally to that interval and match one of its scalars.
    This avoids classifying unrelated insertions elsewhere as boundary duplicates.
    """
    reference = normalize(reference)
    prior_end = 0
    for start, end in intervals:
        if not prior_end <= start <= end <= len(reference):
            raise ValueError("boundary_range")
        prior_end = end
    edits = align(reference, hypothesis)
    duplicates = omissions = denominator = 0
    for start, end in intervals:
        denominator += end - start
        shared = set(reference[start:end])
        duplicates += sum(
            edit.kind == "insertion"
            and start <= edit.reference_index <= end
            and edit.hypothesis in shared
            for edit in edits
        )
        omissions += sum(
            edit.kind == "deletion" and start <= edit.reference_index < end for edit in edits
        )
    return BoundaryCounts(duplicates, omissions, denominator)


@dataclass(frozen=True)
class RewriteCounts:
    changed_pairs: int
    pairs: int
    rewritten_characters: int
    old_characters: int


def rewrite_counts(partials: Sequence[str]) -> RewriteCounts:
    changed = rewritten = total = 0
    normalized = [normalize(text) for text in partials]
    for old, new in pairwise(normalized):
        prefix = 0
        for left, right in zip(old, new, strict=False):
            if left != right:
                break
            prefix += 1
        changed += int(not new.startswith(old) or not new)
        rewritten += len(old) - prefix
        total += len(old)
    return RewriteCounts(changed, max(0, len(normalized) - 1), rewritten, total)


def nearest_rank(values: Sequence[float | int], percentile: float) -> float:
    if not values or not 0 < percentile <= 1 or any(not math.isfinite(v) for v in values):
        raise ValueError("percentile_population")
    return float(sorted(values)[math.ceil(percentile * len(values)) - 1])


def percentiles(values: Sequence[float | int]) -> dict[str, float | int]:
    return {
        "count": len(values),
        "p50": nearest_rank(values, 0.5),
        "p95": nearest_rank(values, 0.95),
    }
