import builtins
from dataclasses import replace
from typing import Literal

import pytest
from pydantic import ValidationError

from tools.asr_benchmark.__main__ import main
from tools.asr_benchmark.contracts import MODELS, NS, Asset, PreparationManifest, Settings
from tools.asr_benchmark.conversion import TensorShape, bind_inference, plan_conversion
from tools.asr_benchmark.preparation import PreparationTransfer
from tools.asr_benchmark.runtime import (
    Allocation,
    BlockedEvidence,
    Budget,
    PrefixScheduler,
    ProgressWatch,
    UnavailableMLXProvider,
    guarded_session,
)

from .factories import DIGEST, inference, preparation


@pytest.mark.parametrize(
    "path",
    [
        "../model.json",
        "/model.json",
        "model.py",
        "a/../model.json",
        "https://host/model.json",
        "a\\model.json",
        "a//b.json",
    ],
)
def test_asset_paths_are_not_execution_or_download_authority(path: str) -> None:
    with pytest.raises(ValidationError):
        Asset(path=path, size=1, sha256=DIGEST, kind="config")


def test_manifest_mirror_parity_and_unknown_fields() -> None:
    manifest = preparation()
    data = manifest.model_dump()
    data["download_url"] = "must-not-be-accepted"
    with pytest.raises(ValidationError):
        PreparationManifest.model_validate(data)
    mirror = manifest.mirrors[1]
    broken = mirror.model_copy(update={"assets": mirror.assets[:-1]})
    data = manifest.model_dump()
    data["mirrors"] = (manifest.mirrors[0], broken)
    with pytest.raises(ValidationError, match="mirror_parity"):
        PreparationManifest.model_validate(data)
    with pytest.raises(ValidationError):
        Settings(output_token_limit=513)  # type: ignore[arg-type]


def test_conversion_requires_exact_classified_inventory_and_shape() -> None:
    manifest = preparation()
    shape = TensorShape(rule=manifest.tensor_map[0], shape=(128, 64))
    assert plan_conversion(manifest, (shape,)).bits == 8
    with pytest.raises(BlockedEvidence, match="inventory_mismatch"):
        plan_conversion(manifest, ())
    with pytest.raises(BlockedEvidence, match="quantization_incompatible"):
        plan_conversion(manifest, (shape.model_copy(update={"shape": (128, 63)}),))
    with pytest.raises(BlockedEvidence, match="preparation_mismatch"):
        bind_inference(manifest, inference(MODELS[1]))


def transfer() -> PreparationTransfer:
    return PreparationTransfer(preparation(), "huggingface", "model.safetensors", 0)


def test_preparation_resume_retry_limits_revision_and_integrity() -> None:
    task = transfer()
    assert task.advance(20, NS).percent == 20
    assert task.failure("transient", NS).outcome == "retry"
    with pytest.raises(BlockedEvidence, match="not_ready"):
        task.resume(task.identity, NS)
    task.resume(task.identity, 2 * NS)
    assert task.received == 20
    assert task.failure("no_progress", 62 * NS).outcome == "retry"
    task.resume(task.identity, 64 * NS)
    assert task.failure("transient", 65 * NS).outcome == "stopped"
    with pytest.raises(BlockedEvidence, match="closed"):
        task.advance(30, 66 * NS)
    task = transfer()
    task.advance(20, NS)
    task.failure("transient", NS)
    with pytest.raises(BlockedEvidence, match="revision_changed"):
        task.resume(("changed", *task.identity[1:]), 2 * NS)
    assert task.received == 0 and task.stopped
    task = transfer()
    task.advance(100, NS)
    assert task.verify(100, DIGEST, NS).outcome == "verified"
    task = transfer()
    task.advance(100, NS)
    with pytest.raises(BlockedEvidence, match="integrity"):
        task.verify(99, DIGEST, NS)


@pytest.mark.parametrize("reason", ["authentication", "permission", "integrity"])
def test_preparation_no_retry_for_auth_or_integrity(
    reason: Literal["authentication", "permission", "integrity"],
) -> None:
    task = transfer()
    assert task.failure(reason, 1).outcome == "stopped"
    assert task.attempt == 1


def test_no_progress_timeout_exact_boundary() -> None:
    task = transfer()
    task.check(60 * NS - 1)
    with pytest.raises(BlockedEvidence, match="no_progress"):
        task.check(60 * NS)


def test_budget_includes_overlap_and_derivatives_before_allocation() -> None:
    released = []
    budget = Budget()
    full = Allocation("full", 0, 30 * NS, 960_000, 960_000)
    budget.reserve(full, lambda: released.append("full"))
    with pytest.raises(BlockedEvidence, match="budget_exceeded"):
        budget.reserve(Allocation("copy", 0, NS, 2, 2), lambda: released.append("copy"))
    budget.release("full")
    budget.reserve(replace(full, allocation_id="features", audio_bytes=16_777_216), lambda: None)
    with pytest.raises(BlockedEvidence, match="budget_exceeded"):
        budget.reserve(Allocation("extra", 0, 1, 1, 0), lambda: None)
    budget.close()
    budget.close()
    assert released == ["full"] and budget.live_count == 0
    with pytest.raises(BlockedEvidence, match="budget_exceeded"):
        budget.reserve(replace(full, end_pts_ns=30 * NS + 1), lambda: None)


def test_cleanup_continues_after_failure_and_blocks_reuse() -> None:
    def fail() -> None:
        raise RuntimeError("private-provider-text")

    budget = Budget()
    released = []
    budget.reserve(Allocation("bad", 0, 1, 1, 0), fail)
    budget.reserve(Allocation("good", 0, 1, 1, 0), lambda: released.append("good"))
    with pytest.raises(BlockedEvidence, match="^teardown_failed$"):
        guarded_session(UnavailableMLXProvider(), budget, fail)
    assert released == ["good"] and budget.live_count == 1
    with pytest.raises(BlockedEvidence, match="teardown_failed"):
        budget.reserve(Allocation("new", 0, 1, 1, 0), lambda: None)


def test_cancel_always_releases_and_sanitizes_provider_failure() -> None:
    def operation() -> None:
        raise RuntimeError("private provider diagnostics")

    budget = Budget()
    released = []
    budget.reserve(Allocation("input", 0, 1, 1, 0), lambda: released.append("input"))
    with pytest.raises(BlockedEvidence, match="^provider_failure$"):
        guarded_session(UnavailableMLXProvider(), budget, operation)
    assert released == ["input"] and budget.live_count == 0


def test_prefix_coalescing_final_priority_and_no_concurrent_calls() -> None:
    scheduler = PrefixScheduler(NS)
    scheduler.arrive(250_000_000)
    assert scheduler.take() is not None
    scheduler.arrive(500_000_000)
    scheduler.arrive(750_000_000)
    assert scheduler.take() is None
    assert scheduler.missed_opportunities == 1
    scheduler.arrive(NS)
    scheduler.close_segment()
    assert scheduler.missed_opportunities == 2
    scheduler.finish()
    final = scheduler.take()
    assert final and final.kind == "final" and final.new_duration_ns == NS
    scheduler.finish()
    assert scheduler.take() is None and scheduler.completed
    assert scheduler.evaluated_prefixes == 1


def test_stall_invalid_pts_and_closed_scheduler() -> None:
    watch = ProgressWatch(0)
    watch.input(0, NS)
    watch.check(3 * NS - 1)
    with pytest.raises(BlockedEvidence, match="input_stall"):
        watch.input(1, 3 * NS)
    with pytest.raises(BlockedEvidence, match="invalid_timing"):
        watch.input(0, NS)
    scheduler = PrefixScheduler(NS)
    scheduler.arrive(NS)
    scheduler.close_segment()
    with pytest.raises(BlockedEvidence):
        scheduler.arrive(NS)


@pytest.mark.parametrize(
    "command",
    [
        ["preflight", "--manifest", "pending"],
        ["run", "--manifest", "pending"],
        ["prepare-models", "--manifest", "pending", "--source", "huggingface"],
    ],
)
def test_cli_closed_without_any_write_or_download(
    command: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("unexpected_file_access")

    monkeypatch.setattr(builtins, "open", forbidden)
    assert main(command) == 2
    output = capsys.readouterr().out
    assert "blocked_evidence" in output
    assert "pending" not in output


def test_cli_rejects_paths_without_echoing_them(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(["run", "--manifest", "/private/secret"])
    assert error.value.code == 2
    assert capsys.readouterr().err == "asr-benchmark: invalid_arguments\n"
