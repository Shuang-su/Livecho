"""Metrics-only report serialization bound to a separately frozen run identity."""

from datetime import date
from typing import TextIO

import rfc8785
from pydantic import ValidationError

from .contracts import Closed, Digest, Identifier, metadata_digest
from .report import Report
from .runtime import BlockedEvidence


class FrozenRun(Closed):
    run_id: Identifier
    scored_on: date
    corpus_sha256: Digest
    machine_sha256: Digest
    privacy_sha256: Digest
    settings_sha256: Digest
    inference_sha256: tuple[Digest, ...]
    preparation_sha256: tuple[Digest, ...]


def run_identity(report: Report) -> FrozenRun:
    """Build metadata for owner review *before* scoring; never grants execution."""
    return FrozenRun(
        run_id=report.run_id,
        scored_on=report.scored_on,
        corpus_sha256=metadata_digest(report.corpus),
        machine_sha256=metadata_digest(report.machine),
        privacy_sha256=metadata_digest(report.privacy),
        settings_sha256=metadata_digest(report.settings),
        inference_sha256=tuple(sorted(metadata_digest(item) for item in report.manifests)),
        preparation_sha256=tuple(sorted(metadata_digest(item) for item in report.preparations)),
    )


def parse_report(text: str, frozen: FrozenRun) -> Report:
    if len(text) > 128 * 1024**2:
        raise BlockedEvidence("report_size")
    try:
        report = Report.model_validate_json(text)
    except (ValidationError, ValueError):
        raise BlockedEvidence("report_invalid") from None
    if run_identity(report) != frozen or report.corpus_sha256 != frozen.corpus_sha256:
        raise BlockedEvidence("frozen_run_changed")
    return report


def serialize_report(report: Report, frozen: FrozenRun) -> str:
    try:
        text = rfc8785.dumps(report.model_dump(mode="json")).decode("utf-8")
    except (ValueError, TypeError):
        raise BlockedEvidence("report_invalid") from None
    parse_report(text, frozen)
    return text


def write_report(report: Report, frozen: FrozenRun, sink: TextIO) -> None:
    """Use the operator's already-open metrics sink; accepts no path or URL."""
    text = serialize_report(report, frozen)
    try:
        if sink.write(text) != len(text):
            raise BlockedEvidence("report_write_failed")
        sink.flush()
    except Exception:
        raise BlockedEvidence("report_write_failed") from None
