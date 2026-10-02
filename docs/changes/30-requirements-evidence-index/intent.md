# Intent: Make requirement authority and capability evidence traceable

## Issue and owner

- GitHub Issue: [#30](https://github.com/Shuang-su/Livecho/issues/30)
- Human owner: @Shuang-su
- Area/risk: documentation and engineering governance; no new data processing
- Prerequisites: Issues #2, #3, and #4

## Problem

Architecture, audio, protocol, security, identity, deletion, recovery, and deployment
requirements are spread across accepted artifacts and supporting records. Their merge
status, implementation ownership, evidence, and approval state are different facts.
Readers can currently mistake a merged contract for a working service or apply a
production prerequisite to a local synthetic caption demonstration. README and roadmap
also lag the merged protocol/deployment skeleton and the current Issue dependencies.

## Desired outcome

After this artifact is owner-merged, implement a documentation index that traces each
requirement to one primary definition, its owning Issue, scoped verification evidence,
and the capabilities/stages it blocks. Make README describe the merged foundation,
protocol package, and offline deployment skeleton accurately while stating that the
business runtime chain and deployed environments are not established. Make roadmap
follow GitHub's actual dependency edges: controlled audio and a single-worker local
caption loop can precede platform ingest and independent event display.

The index is navigation and evidence accounting. It cannot create, supersede, approve,
or weaken a requirement. A reader must be able to tell what exists, what is required,
what remains unverified, and which specific human decision is still pending.

## Non-goals

- Reopening completed Issues #1–#4 or changing their accepted intent/spec/plan.
- Implementing runtime, protocol, UI, infrastructure, CI, or a new validation tool.
- Approving ADR 0001, accepting residual risks, selecting a platform acquisition
  channel, granting rights, enabling production, or running hardware/provider checks.
- Resolving a normative conflict by choosing the most convenient document.
- Making #30, #27, #28, or #29 a new prerequisite for #9/#11's short local synthetic
  demonstration when their owning Issues do not require that edge.
- Adopting the pending [#31](https://github.com/Shuang-su/Livecho/issues/31) proposal,
  “开放贡献闭环、可信统计及字幕体验”, as approved requirements.

## Constraints and data impact

This artifact PR changes only this Issue's four records. The index, README, and roadmap
are a separate documentation implementation after the owner merges intent/spec/plan.
Existing audio ephemerality, credential isolation, worker distrust, protocol
compatibility, restricted data, deletion/recovery, and CUDA mock-only rules continue to
apply at their existing scope. No production data, audio, credentials, upstream
expression, external research report, or deployment artifact is an input or output.

Data classification: repository requirements, public Issue metadata, and public-safe
verification metadata only. Missing evidence remains missing; a reference to restricted
operational evidence must not disclose its contents.

## Success signal

A reviewer can start with any covered requirement and reach its definition, governance
state, responsible Issue, and exact evidence without inferring capability from a merge,
closed Issue, unchecked box, proposed design, or offline test. Local synthetic work has
a clear path, and production-only blockers remain explicit and intact.

## Human decision

- Status: Proposed; artifact review only
- Approved by/date: Pending
- This draft and its PR do not approve implementation or any production capability.
