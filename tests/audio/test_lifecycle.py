from __future__ import annotations

import pytest
from livecho_backend.audio.contracts import AudioError, Reason
from livecho_backend.audio.ledger import Interval
from livecho_backend.audio.lifecycle import Lifecycle, Metrics, State


def running() -> Lifecycle:
    lifecycle = Lifecycle(restartable=True)
    lifecycle.start(0, admitted=True)
    lifecycle.progress(20, canonical=True)
    return lifecycle


def test_start_deadline_exactly_two_seconds() -> None:
    lifecycle = Lifecycle(restartable=False)
    lifecycle.start(0, admitted=True)
    lifecycle.progress(1999)
    lifecycle.tick(2000)
    assert lifecycle.reason == Reason.DECODER_START_TIMEOUT
    assert not lifecycle.gate_open


def test_input_stall_and_pause_exclusion() -> None:
    lifecycle = running()
    lifecycle.pause(100)
    assert lifecycle.resume(599, reserved=True, admitted=True)
    lifecycle.tick(2518)
    assert lifecycle.state == State.RUNNING
    lifecycle.tick(2519)
    assert lifecycle.reason == Reason.INPUT_STALLED
    assert lifecycle.metrics.pause_ms == 499


@pytest.mark.parametrize("release,success", [(499, True), (500, False), (501, False)])
def test_consumer_pause_boundary(release: int, success: bool) -> None:
    lifecycle = running()
    lifecycle.pause(100)
    assert not lifecycle.gate_open
    assert lifecycle.resume(100 + release, reserved=True, admitted=True) == success
    if not success:
        assert lifecycle.reason == Reason.CONSUMER_SLOW


def test_slow_consumer_fails_even_without_returning_to_pipeline() -> None:
    lifecycle = running()
    lifecycle.pause(100)
    lifecycle.tick(600)
    lifecycle.cleaned(600, reaped=True, admitted=True)
    assert lifecycle.state == State.FAILED
    assert lifecycle.metrics.retries == 0


def test_session_retry_budget_never_resets_after_success() -> None:
    lifecycle = running()
    lifecycle.abort(Reason.INPUT_STALLED)
    lifecycle.cleaned(100, reaped=True, admitted=True)
    assert not lifecycle.retry_due(349, admitted=True)
    assert lifecycle.retry_due(350, admitted=True)
    lifecycle.start(350, admitted=True)
    lifecycle.progress(370, canonical=True)
    lifecycle.abort(Reason.DECODER_PIPE)
    lifecycle.cleaned(400, reaped=True, admitted=True)
    assert not lifecycle.retry_due(1399, admitted=True)
    assert lifecycle.retry_due(1400, admitted=True)
    lifecycle.start(1400, admitted=True)
    lifecycle.progress(1420, canonical=True)
    lifecycle.abort(Reason.DECODER_EXIT)
    lifecycle.cleaned(1440, reaped=True, admitted=True)
    assert lifecycle.state == State.FAILED
    assert lifecycle.metrics.retries == 2
    assert lifecycle.continuity_broken


@pytest.mark.parametrize(
    "reason",
    [
        Reason.CANCELLED,
        Reason.DISABLED,
        Reason.DENYLISTED,
        Reason.SESSION_END,
        Reason.LEASE_END,
        Reason.SHUTDOWN,
    ],
)
@pytest.mark.parametrize("during_retry", [False, True])
def test_stop_invalidates_pending_generation_and_no_retry(
    reason: Reason, during_retry: bool
) -> None:
    lifecycle = running()
    old = lifecycle.generation
    if during_retry:
        lifecycle.abort(Reason.DECODER_EXIT)
        lifecycle.cleaned(100, reaped=True, admitted=True)
    lifecycle.abort(reason, terminal=True)
    assert not lifecycle.gate_open
    assert lifecycle.generation != old
    lifecycle.cleaned(200, reaped=True, admitted=True)
    assert lifecycle.state == State.STOPPED
    assert not lifecycle.retry_due(5000, admitted=True)


def test_deny_after_retry_delay_or_reap_failure_blocks_replacement() -> None:
    lifecycle = running()
    lifecycle.abort(Reason.DECODER_EXIT)
    lifecycle.cleaned(100, reaped=True, admitted=True)
    assert not lifecycle.retry_due(350, admitted=False)
    with pytest.raises(AudioError):
        lifecycle.start(350, admitted=True)
    lifecycle.cleaned(400, reaped=False, admitted=True)
    assert lifecycle.state == State.FAILED
    assert lifecycle.reason == Reason.DECODER_REAP_FAILED
    with pytest.raises(AudioError):
        lifecycle.start(10000, admitted=True)


def test_eof_never_reconnects() -> None:
    lifecycle = running()
    lifecycle.eof(100, handle_pending=False)
    lifecycle.cleaned(100, reaped=True, admitted=True)
    assert lifecycle.state == State.STOPPED
    assert lifecycle.metrics.retries == 0


def test_drop_unique_union_does_not_double_count_overlap() -> None:
    metrics = Metrics()
    metrics.drop(Reason.CONSUMER_SLOW, [Interval(0, 6000), Interval(5200, 11200)])
    assert metrics.dropped_ms == {Reason.CONSUMER_SLOW: 11200}
    assert metrics.unmeasurable_input == 0
