import math

import pytest

from tools.asr_benchmark.metrics import (
    align,
    boundary_counts,
    error_counts,
    nearest_rank,
    normalize,
    percentiles,
    rewrite_counts,
    stitch,
    target_exact,
)


def test_normalization_preserves_script_variants_digits_symbols_and_non_ascii_case() -> None:
    assert normalize(" e\u0301\uff0c\uff21A 中 國国 12 + 🐈!\n") == "é\uff21a中國国12+🐈"
    assert normalize("三十 30") == "三十30"


def test_alignment_ties_are_forward_substitution_before_deletion() -> None:
    edits = align("ab", "ba")
    assert [edit.kind for edit in edits] == ["substitution", "substitution"]
    assert [edit.kind for edit in align("aab", "ab")] == ["match", "deletion", "match"]
    counts = error_counts("中国abc", "中xabc多")
    assert (counts.substitutions, counts.deletions, counts.insertions) == (1, 0, 1)
    assert counts.cer == 0.4
    assert error_counts("", "幻觉").cer is None
    assert error_counts("", "幻觉").insertions == 2
    assert error_counts("🐈中", "中").deletions == 1


def test_target_exact_does_not_accept_a_matching_substring_elsewhere() -> None:
    assert target_exact(align("北京欢迎你", "北京欢迎你"), 0, 2)
    assert not target_exact(align("北京欢迎你", "上海欢迎你北京"), 0, 2)
    assert not target_exact(align("北京", "北小京"), 0, 2)


def test_stitch_longest_exact_match_is_bounded() -> None:
    assert stitch(("今天去北京", "北京看花", "看花很好")) == "今天去北京看花很好"
    assert stitch(("甲乙", "丙丁")) == "甲乙丙丁"
    assert len(stitch(("甲" * 40, "甲" * 40))) == 48


def test_boundary_counts_are_local_and_zero_coverage_is_not_a_pass() -> None:
    duplicate = boundary_counts("甲乙丙丁", "甲乙乙丙丁", ((1, 2),))
    assert (duplicate.duplicates, duplicate.omissions, duplicate.reference_characters) == (1, 0, 1)
    omitted = boundary_counts("甲乙丙丁", "甲丙丁", ((1, 2),))
    assert omitted.omissions == 1
    assert boundary_counts("甲乙丙丁", "乙甲乙丙丁", ((1, 2),)).duplicates == 0
    assert boundary_counts("甲", "甲", ((0, 0),)).reference_characters == 0
    with pytest.raises(ValueError, match="boundary_range"):
        boundary_counts("甲乙", "甲", ((1, 2), (0, 1)))


def test_partial_extensions_withdrawals_and_severity() -> None:
    counts = rewrite_counts(("北京", "北京欢迎", "北京欢送", ""))
    assert (counts.changed_pairs, counts.pairs) == (2, 3)
    assert (counts.rewritten_characters, counts.old_characters) == (5, 10)
    assert rewrite_counts(("a", "ab", "abc")).changed_pairs == 0
    assert rewrite_counts(("", "")).changed_pairs == 1


@pytest.mark.parametrize("bad", [[], [math.nan], [math.inf], [-math.inf]])
def test_invalid_percentile_populations(bad: list[float]) -> None:
    with pytest.raises(ValueError, match="percentile_population"):
        nearest_rank(bad, 0.95)


def test_nearest_rank_boundaries() -> None:
    assert percentiles((3, 1, 2)) == {"count": 3, "p50": 2, "p95": 3}
    assert nearest_rank(tuple(range(1, 21)), 0.95) == 19
    assert nearest_rank((7,), 0.5) == 7
    with pytest.raises(ValueError):
        nearest_rank((1,), 0)
