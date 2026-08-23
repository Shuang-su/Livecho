# Intent: Approve Alpha architecture and risk boundaries

## Issue and owner

- GitHub Issue: #2
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m0`, `area:architecture`, `type:security`, `risk:high`

## Problem

Livecho currently has no owner-approved boundary between the public browser, the
authoritative backend, Bilibili, community workers, or managed data processors. The
repository also lacks one auditable decision for audio ephemerality, long-lived event
data, takedown and deletion recovery, public-ingest eligibility, emergency disablement,
and independent implementation around differently licensed reference projects. Later
Issues would otherwise make incompatible or unsafe choices in runtime code.

## Desired outcome

Approve a documentation-only Alpha architecture in which a modular-monolith backend is
the sole authority for sessions, authorization, sequencing, persistence, and safety
controls. The accepted documentation will:

- draw every required trust boundary and allowed or prohibited data flow;
- define role ownership, a production-default-off ingest switch, and a room denylist;
- classify transient audio and playback secrets separately from restricted-by-default
  normalized/raw data, identity, audit, and deletion data;
- require fail-closed public-ingest and platform-policy decisions;
- provide a threat model, deletion/recovery procedure, and incident tabletop; and
- establish provenance and clean-room rules for MIT, AGPL, mixed, or unclear upstream
  material.

These records become constraints for subsequent protocol, ingest, worker, identity,
storage, and deployment Issues. Production ingest remains disabled until its stated
preconditions and the repository owner's residual-risk approval are recorded.

## Non-goals

- Implementing runtime code, APIs, protocol schemas, database migrations, deployment
  resources, or live platform access.
- Treating public availability as permission to record, transform, redistribute, or
  retain a stream or its events.
- Finalizing wire-level `epoch`, `seq`, or `revision` behavior reserved for Issue #3.
- Copying or adapting source, tests, fixtures, schemas, configuration, comments, or
  assets from AGPL or license-unclear reference projects.
- Enabling production ingest or accepting final residual risk in the artifact pull
  request.

## Constraints and data impact

- This Issue changes documentation only and processes no production or personal data.
- Audio is ephemeral in every conforming Livecho component: each room/session or worker
  lease may hold at most 30 seconds in bounded RAM, and no PCM, encoded audio, audio
  base64, stream buffer, or derived audio artifact may be persisted. An untrusted worker
  host can violate that rule, so identity and lease checks are not treated as proof of
  erasure; real-audio assignment remains production-disabled until its named residual
  risk and third-party-processing rights basis are separately approved.
- Workers receive only versioned, bounded ASR messages and allowlisted model manifests;
  they receive no platform, database, archive, email, playback, or encryption secret.
- Public ingest is limited to operator-selected, free, anonymous, currently live rooms
  and stops on any login, payment, geographic, DRM, policy, or rate-limit boundary.
- Normalized events and sanitized encrypted raw business payloads remain restricted and
  production persistence is disabled until Issue #16 implements access, audit, deletion,
  and recovery controls and an owner-approved source record permits that purpose. Issue
  #16 has no platform-independent automatic TTL; this is not unlimited authorization,
  and a stricter source, rights, law, or policy rule always wins.
- Platform rules, rights evidence, processor behavior, and upstream licenses are
  time-varying external dependencies. Their exact authoritative source, capture date,
  immutable revision where applicable, and review owner must be recorded; ambiguity
  disables the affected path.
- Data classification: restricted normalized events with only an explicitly approved
  real-time subset public; restricted identity and worker metadata; high-risk sanitized
  raw business payloads; secrets and transient playback locators; deletion manifests
  and payload-free audit records; ephemeral audio.

## Success signal

A reviewer can trace each required component, data class, actor, threat, disable path,
and deletion step from the Issue acceptance criteria into an owner-approved ADR and
supporting documents. The repository owner separately records final ADR approval and
residual-risk acceptance before any production ingest is enabled.

## Human decision

- Status: Approved for artifact review and merge; final ADR and residual-risk approval
  remains an implementation acceptance criterion.
- Approved by/date: @Shuang-su / 2026-08-24 (authorized this agent to continue and merge
  after repository checks and review gates pass).
