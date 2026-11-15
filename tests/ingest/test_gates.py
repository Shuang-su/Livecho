from __future__ import annotations

from livecho_backend.ingest.gates import (
    ACQUISITION_CHANNELS,
    ENCODED_ADMISSION_EVIDENCE,
    PRODUCTION_INGEST_DEFAULT,
    RIGHTS_EVIDENCE,
    evidence_blockers,
    real_acquisition_allowed,
)


def test_checked_in_registries_remain_closed() -> None:
    assert ACQUISITION_CHANNELS == ()
    assert RIGHTS_EVIDENCE == ()
    assert ENCODED_ADMISSION_EVIDENCE == ()
    assert PRODUCTION_INGEST_DEFAULT is False
    assert not real_acquisition_allowed()
    blockers = evidence_blockers()
    assert "acquisition_channel_unselected" in blockers
    assert "rights_basis_missing" in blockers
    assert "encoded_admission_missing" in blockers
    assert "audio_budget_unverified" in blockers
