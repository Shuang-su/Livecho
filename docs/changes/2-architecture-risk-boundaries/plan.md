# Implementation plan: Approve Alpha architecture and risk boundaries

## Order of work

1. Capture authoritative, current Bilibili terms/policy sources, exact acquisition
   channel/API family, agreement applicability, and platform/rights-holder permission
   evidence. Capture canonical LAPLACE/Chatterbox-related upstream repositories by
   immutable revision and path/package with the nearest license and digest. Record
   retrieval/effective dates and any ambiguity; ambiguity keeps the affected path off.
2. Write `docs/architecture/adr/0001-alpha-modular-monolith.md` with the accepted
   modular-monolith decision, maintenance-job exception, alternatives, consequences,
   owner/risk gate, and a Mermaid diagram containing every required trust zone, safety
   recovery/admin-export boundary, allowed flow, and prohibited flow.
3. Write `docs/security/alpha-threat-model.md` with assets, actors, entry points, the
   complete required threat set, anonymous/invited role matrix, malicious-worker audio
   retention and control-state rollback threats, preventive/detective/response controls,
   residual severity, control owner, and explicit Critical/High acceptance fields.
4. Write `docs/security/data-lifecycle-and-deletion.md` with the normative data-class
   matrix, media-time and per-session/lease/process audio ceilings, zero-persistence
   paths, source-specific retention gates, account/bearer/device/audit/export bounds,
   three deletion states without physical-erasure claims, 24-hour active-store SLA,
   backup evidence, tombstones, and restore replay gate. Trace future enforcement to
   Issues #8, #10, #12, #13, and #16.
5. Write `docs/policy/bilibili-public-ingest.md` with canonical room selection,
   eligibility/denial rules, acquisition channel/terms applicability, written permission
   evidence where required, worker-processing and output-use rights, 90-day/change
   recheck, takedown contact, and owner enablement record. Trace runtime to Issue #7.
6. Write `docs/policy/independent-implementation.md` with per-upstream provenance,
   path-level revision/license classification, author exposure/exclusion record,
   independently written requirements, AGPL/mixed/unclear clean-room prohibitions,
   mandatory MIT notice mapping, model/dataset separation, and isolated
   post-implementation reviewer attestation.
7. Write `docs/operations/incident-disable-and-recovery.md` with operator/admin actions,
   global switch and denylist transitions, monotonic safety journal/recovery copy,
   fail-closed dependencies, lease/audio/locator cleanup, deletion partial-failure and
   export handling, restore-forced-off replay, re-enable prerequisites, audit fields, and
   the paper/tabletop scenarios.
8. Link the approved records from `README.md` and `SECURITY.md`, update only Issue #2's
   `evidence.md`, and verify the diff contains documentation and no runtime or deployment
   resources.
9. Run deterministic checks and independent security/license/data review. Resolve every
   P1/P2 or document a scoped lower-severity residual. Obtain @Shuang-su's explicit ADR
   approval and individual Critical/High residual-risk decisions before merge or any
   production enablement.

## Verification

- `make bootstrap`
- `make verify`
- `git diff --check`
- `git diff --name-only origin/main...HEAD`
- Manual diagram trace: each required zone, allowed flow, prohibited flow, and secret
  boundary maps to a stable identifier in the ADR.
- Manual threat/lifecycle trace: every Issue #2 threat and data class has an owner,
  control, failure response, retention/deletion rule, and residual status.
- Tabletop 1: operator global-disable during an active room revokes the lease, clears
  transient audio/locator state, blocks reconnect, and records a payload-free audit.
- Tabletop 2: room takedown with one failed object deletion remains hidden/denied,
  retries idempotently, and cannot report completion.
- Tabletop 3: backup restore replays the latest deletion manifest successfully before
  reconciling the current safety generation/denylist; the environment stays forced off
  until both replays succeed and no viewer or ingest traffic is accepted.
- Tabletop 4: an authenticated worker is treated as able to copy PCM; the synthetic-only
  default, explicit third-party rights gate, named residual-risk decision, least-data
  ceiling, revocation, and incident response are all traced without claiming erasure.
- Source/provenance review: every platform and upstream claim points to an authoritative
  source/version; no prohibited AGPL/mixed/unclear material or real secret/audio/raw
  fixture entered the repository.

## Rollout and rollback

This is documentation-only and has no environment rollout or migration. Merging the
implementation makes the constraints mandatory while production ingest remains
disabled. A later Issue may implement one control only after its dependencies are
merged and verified. A documentation error or external-policy change triggers the
global disable posture and a corrective Issue/ADR; rollback must not silently weaken
audio, credential, worker, raw-access, deletion, or platform restrictions.

## Open decisions

None. Exact external revisions, policy effective dates, applicable acquisition terms,
permission evidence, provider backup limits, and residual findings are evidence gathered
by the ordered work, not discretionary product choices. If authoritative evidence is
missing/expired, a bounded retention/recovery property cannot be demonstrated, or a
Critical/High risk is unaccepted, the corresponding production capability remains
disabled.
