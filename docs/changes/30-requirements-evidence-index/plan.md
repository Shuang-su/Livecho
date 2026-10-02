# Implementation plan: Requirement authority and evidence index

## Order of work

1. Review and owner-merge this artifact-only PR. Start the documentation implementation
   on a separate Issue #30 branch based on that merge. Do not add the index or update
   README/roadmap before that gate.
2. Before implementation authorship, commit each author's fresh exposure and assignment
   record to this Issue's evidence, including every direct or summarized source viewed
   and a named independent reviewer. Reference-only material and research reports do
   not enter the requirements or implementation context.
3. Read the owning Issue and accepted artifacts at the implementation base, the complete
   architecture/security/lifecycle/policy/operations records being indexed, and the
   relevant protocol contract/evidence. Capture the source revision and date. Recheck
   #1–#19 and #27–#30 Issue state/dependencies and merged PR evidence without treating a
   closed Issue as technical or governance approval. #31 remains a title-only pending
   proposal unless a separate owner-merged change explicitly supplies new authority.
4. Enumerate stable identifiers and definition sections. Assign each one primary
   definition only where the accepted source responsibilities establish it; preserve
   all supporting references and source status. Record ambiguity, contradictory wording,
   approval gaps, and ownership mismatches in the conflict register rather than changing
   the source or inventing precedence.
5. Create `docs/requirements-index.md` with the required row fields, evidence dimensions,
   capability/stage applicability, unresolved register, and dated baseline. Populate
   missing evidence explicitly. Audit coverage against the actual identifier inventory,
   protocol/deployment sections, and each Issue #30 acceptance criterion.
6. Update README with the exact merged repository scope and remaining business/runtime
   work. Link index and roadmap and show the local synthetic caption path. Update roadmap
   with current direct Issue edges and conditional capability gates, including #27/#28/
   #29 and the title-only pending #31 entry. Keep production approvals separate.
7. Verify every local file/section/ID link, public Issue/PR link, evidence scope/date/
   revision, stable-ID coverage, owner mapping, direct dependency edge, and approval
   statement. Compare README/roadmap summaries against the index and sources. Record the
   exact audit script/commands, counts, exclusions, result, and checked revision in
   `evidence.md`; no checker or new dependency is added to the repository by this Issue.
8. Run the full deterministic repository checks. Have a separate reviewer trace at least
   the local #9/#11 path, #27 lifecycle gate, #28 real-input gate, #29 event delivery,
   proposed ADR/unaccepted risks, data deletion/recovery, and offline-versus-live Railway
   claims. The reviewer reports source-based findings without relaying reference-only
   expression and does not patch the work.
9. Open one documentation implementation PR closing #30 only after its artifacts are
   already in the base. Record any new normative decision as a separate proposed change;
   do not bundle or infer it. Owner review/merge remains a separate action.

## Verification

For this artifact PR and the later documentation implementation:

- `make bootstrap`
- `make verify`
- `make artifacts`
- `git diff --check`
- `git diff --cached --check`
- `git diff --name-only origin/main...HEAD`

The artifact PR must contain exactly `intent.md`, `spec.md`, `plan.md`, and `evidence.md`
under `docs/changes/30-requirements-evidence-index/`. The implementation path allowlist is
`docs/requirements-index.md`, `README.md`, `docs/roadmap.md`, and this Issue's
`evidence.md`; accepted intent/spec/plan remain unchanged.

The implementation evidence must include the complete exact commands/scripts for:

- relative file and section/ID existence, including all Markdown links in the deliverables;
- stable-ID inventory versus index records, duplicates and unresolved authority counts;
- GitHub Issue state/direct-dependency snapshots, their capture date, and differences
  from roadmap (only known Livecho Issues, with #31 title-only);
- the manual source/approval/evidence cross-check and selected capability traces above;
- scope verification and an unchanged accepted-artifact comparison against the base.

Use ephemeral audit scripts where useful and record their exact contents in evidence.
Do not present a text search, document link, paper review, test pass, or Issue closure as
live technical enforcement. No hardware, provider, production or real-audio test belongs
to this documentation change.

## Rollout and rollback

This artifact rollout ends at a draft PR for owner review. It creates no operational
capability. After approval, the implementation rollout ends at merged documentation;
there is no deploy, migration, resource creation, feature enablement, or external message.
Revert or correct the documentation if navigation/status is wrong while preserving
accepted source decisions and historical evidence. A normative change needs its own
reviewed artifact; documentation rollback cannot approve or disable a runtime control.

## Open decisions

Owner approval of this proposed artifact is pending. No implementation design choice is
delegated implicitly: format, evidence dimensions, source responsibilities, phase scope,
deliverables, and conflict handling are specified here. The source index may truthfully
contain unresolved normative conflicts; those are separate owning-Issue decisions, not
permission for #30 to resolve them. #31 remains pending and supplies no requirements.
