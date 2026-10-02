# Specification: Requirement authority and evidence index

## Behavior

### Deliverables and authority

After this artifact merges, the Issue #30 documentation implementation adds
`docs/requirements-index.md`, updates `README.md` and `docs/roadmap.md`, and records its
verification in this directory's `evidence.md`. It changes no other accepted decision
or runtime path. The index links back to #30 as its maintenance owner and states its
review date and the repository commit used for its source audit.

The index is a secondary navigation record. Accepted Issue artifacts define approved
intent and contracts; supporting records retain their explicitly recorded approval
state. GitHub Issues supply current planning status and dependency declarations, not
approval of unmerged specifications. Evidence supplies only the claim actually checked.
README and roadmap summarize these sources and never replace them. There is no
automatic “newest document wins” or “closed Issue means approved” rule.

Each requirement has exactly one primary definition pointer with a file and section or
existing stable identifier. Related specifications, procedures, tests, and repeated
mentions are supporting pointers, not competing definitions. Reuse existing `DEC-*`,
`FLOW-*`, `CTRL-*`, `DATA-*`, `THREAT-*`, `RISK-*`, `BILI-*`, and `LIC-*` identifiers;
do not rename them or invent new runtime/protocol identifiers. Where no identifier
exists, the index may use a stable, local `IDX-*` navigation ID with no wire meaning.
Distinct independently testable conditions must not be collapsed into one green row.

Primary pointers follow a source's explicitly assigned responsibility. If that assignment
is ambiguous or two definitions conflict, mark the row `authority unresolved`, link both
locations, and record the discrepancy in a conflict register. Do not silently select,
deduplicate, reconcile, or edit the rules. The affected capability remains blocked where
the unresolved difference affects its gate; unrelated capabilities keep their own status.
A separate owner-reviewed normative change must resolve a substantive conflict before
the index can record one unambiguous primary definition. An accurately recorded unresolved
conflict does not itself prevent delivery of this navigation index.

### Required row content

The index may split wide tables into linked row records for readability. Every record
must retain all of these fields:

| Field | Required content |
| --- | --- |
| Requirement | Existing stable ID or local navigation ID and a short faithful summary. |
| Primary definition | Exactly one path plus section/ID; or explicit unresolved status with all candidate pointers. |
| Source/governance state | Accepted artifact, merged proposed record, unmerged proposal, or unresolved; link the exact approval record when one exists. |
| Ownership | Definition-owning Issue and every implementation/evidence-owning Issue already assigned by the source; distinguish those roles from #30's index maintenance. |
| Capability and stage | Explicit affected capability, applicable stage(s), and any prerequisite condition that activates the gate. |
| Current implementation fact | Implemented scope and commit/PR link, or `not implemented` / `not established`; no inference from documentation alone. |
| Evidence | Category, exact evidence link/section, checked command or observation, result, date, revision/environment where relevant, and limits. Use `missing` if absent. |
| Blocker | Required missing evidence/decision, responsible Issue or human role, affected capability, and resolution pointer; use `not applicable` only with a reason. |

The evidence categories are separate dimensions, never a score or a promotion ladder:

| Category | What it can establish | What it cannot establish |
| --- | --- | --- |
| Document constraint / paper review | Recorded requirement, reviewed design, or tabletop outcome. | Running enforcement, hardware behavior, deployment, rights, or owner approval. |
| Offline contract verification | Named deterministic tests at a specific revision and their bounded synthetic scope. | A business integration, real ASR quality/performance, provider state, or production enablement. |
| Runtime/integration verification | Named exercised path, input class, version, duration, environment, and result. | Unexercised paths, rights, hardware/provider facts absent from the evidence, or blanket readiness. |
| Real hardware verification | Trusted manual measurements with identified hardware, software/model version, workload provenance, and limits. | CUDA implementation from a mock, different hardware/model performance, or rights approval. |
| Deployment/provider verification | Exact environment's redacted observed controls and rollout result. | Other environments, guarantees from an offline desired-state render, or approval to enable production. |
| Owner/governance decision | Named approver, date, exact scope/revision, and any review/expiry conditions. | Platform/right-holder permission or technical enforcement. |

External rights/source evidence remains a separately linked prerequisite with issuer,
scope, review/expiry state, and its source record. A governance signature cannot replace
it. The index does not perform a new legal, platform-policy, provider, or license review.
It reports the dated existing record and any explicitly missing/expired condition.

Evidence results are `passed`, `failed`, `pending`, `missing`, or `not applicable` with
scope and reason. A changed or out-of-scope revision/environment is not current proof.
Historical successful results remain visible as historical evidence, not deleted or
silently promoted. A capability is described as available only when all gates applicable
to that capability have the required evidence; no single combined “done” checkbox is
permitted to substitute for the dimensions above.

### Coverage and source responsibilities

The implementation must enumerate, rather than merely link a folder containing, all
existing stable decisions, flows, controls, data classes, threats, residual risks,
platform decisions/rights rows, and license/exposure gates in the following scope.
Repeated instances of a stable ID form one record with supporting pointers. Protocol
and deployment sections without stable IDs receive traceable navigation records at the
granularity needed to expose independently applicable gates.

| Area | Source records and required distinctions |
| --- | --- |
| Repository lifecycle | `AGENTS.md`, `CONTRIBUTING.md`, `docs/changes/README.md`, Issue #1 artifacts: artifact-before-implementation and human merge authority. |
| Architecture and trust | Issue #2 artifacts and ADR 0001: one authoritative backend, constrained maintenance, permitted/prohibited flows, roles, and final ADR decision state. |
| Security and residual risks | Threat model: every named threat/control and individual risk acceptance; a merged threat table is not acceptance. |
| Audio and worker boundary | Lifecycle, architecture, and Issues #2/#3: RAM ceilings/cleanup, no persistence, backend-only locators/secrets, synthetic-only lease, allowlisted protocol/model references, and hostile-host retention residual. |
| Protocol and live lifecycle | Issue #3 artifacts/evidence and its source/generated contract: ordering, bounded state, revision/final/reconnect semantics and compatibility; #27 and #28 remain later owning Issues with separate evidence. |
| Platform and publication | Bilibili policy: exact channel, eligibility, acquisition/transformation/disclosure/retention/publication rights, review triggers, takedown contacts, and production-off state. |
| Data, deletion, identity, and restore | Lifecycle and incident records: restricted normalized versus encrypted raw boundaries, typed room/session deletion, identity/device revocation, durable intake, current safety state, backup/export windows, truthful completion, and restore isolation. |
| Deployment and secrets | Issue #4 artifacts plus Railway deployment/secrets records: offline skeleton versus live resources, default-off flags, environment isolation, immutable builds, maintenance admission/fencing, credential lifecycle, rollout/rollback, and provider proof. |
| Independent implementation | License policy: accepted-source requirements, exposure/assignment records, separate reviewer, reference-only exclusions, notices and independent model/dataset provenance. |
| Delivery and user-visible scope | Current owning Issues: local caption loop, platform integration, independent event Web, identity/stats/history, mock CUDA, and final Alpha acceptance. |

A definition-owner/evidence-owner discrepancy must be preserved and reviewed, not
resolved by assigning all controls to #30. Source requirements and their detailed
approval wording remain linked; the index summary must not narrow their scope.

### Stages and dependencies

Stage labels express applicability; they do not authorize an activity:

- **Repository/offline contract:** artifacts, pure protocol tests, offline deployment
  renders, synthetic metadata, and memory-only synthetic codec tests.
- **Local synthetic caption demonstration:** #8's controlled audio path, #6's synthetic
  worker path, #9's short single-worker integration, and #11's caption/session-status
  companion page. Each still needs its own merged artifact and required verification.
- **Trusted hardware validation:** only the owning hardware Issue's approved manual
  scope; no model/data download or real inference is authorized by this index.
- **Platform/real-input capability:** all applicable source/rights, safety, protocol,
  recipient, and individual risk gates; a permitted real recording is not synthetic.
- **Distributed, persistence, and identity capability:** owning Issues' gateway,
  scheduling, authorization, retention, deletion, and recovery requirements apply to
  their named capability, rather than to every local demonstration.
- **Provider staging/production:** actual environment and deployment evidence plus
  scoped owner decisions; production does not inherit staging approval or credentials.

Universal boundaries such as audio ephemerality, secret isolation, worker distrust, and
protocol compatibility still apply to every relevant local or production path.
Production rights, provider, persistence, and named residual-risk approval gates must not
be described as prerequisites for a purely local synthetic path that does not exercise
those capabilities. Conversely, calling a real/platform path a demo cannot exempt it.

At implementation review, roadmap records every current Issue's direct prerequisites
with links and a capture date, based on GitHub rather than Issue-number ordering. Keep
direct dependencies separate from conditional production gates. The following owning
relationships must be visible, subject to rechecking the Issues rather than silently
freezing this snapshot:

- #8 depends on #2/#3; #6 on #3/#5; #9 on #3/#6/#8; #11 on #3/#9.
- #7 follows #2/#3/#8; #10 follows #2/#3/#7; #29 follows #10/#11.
- #27 follows #3, owns long-session capacity/lifecycle/resynchronization and supplies
  #15/#19. Its pending work does not block #9's short synthetic demonstration.
- #28 follows #2/#3, owns real-input source/capability negotiation and supplies #19.
  Current #6/#9 synthetic work uses the existing synthetic-only contract.
- #29 owns danmaku/Super Chat display after #10/#11 and supplies #19; #11's first page
  remains caption/session-status scoped despite its broader Issue title.
- #30 follows #2/#3/#4 and owns this index; it adds no gate to #9/#11.
- #31 is listed only as the pending proposal “开放贡献闭环、可信统计及字幕体验”. No
  new role, public enrollment, statistics metric, UI behavior, dependency, or change to
  accepted restrictions may be inferred from that title or from #30's merge.

If GitHub edges and accepted artifacts disagree, record the exact discrepancy; an Issue
edit alone cannot override an accepted normative contract. A refresh must not silently
approve new scope. All other #5–#19 dependencies remain traceable in the roadmap audit.

### README and maintenance behavior

README must name the engineering foundation, protocol v1 package with deterministic
cross-language verification, and offline Railway skeleton as merged repository work.
It must distinguish those from the unimplemented business runtime chain and unestablished
provider environments. It must link the index and roadmap, lead readers to the local
synthetic caption path, and preserve production-off and CUDA mock-only qualifications.

An owning Issue's later implementation, evidence, approval, dependency, or source-status
change triggers review of its index rows and affected README/roadmap summaries. Updates
retain the prior source/evidence history and use normal PR review; no automation or
automatic approval is introduced. #30 records the maintenance convention without editing
other Issues or reopening completed work.

## Interfaces and compatibility

Only Markdown navigation and summaries change after artifact approval. There is no API,
schema, runtime config, protocol `epoch`/`seq`/`revision`, generated output, CI, tool,
dependency, or database change. Existing normative files and stable identifiers remain
unchanged. Local links use repository-relative paths and valid sections/identifiers;
GitHub links point to the exact Issue, PR, or evidence record.

## Failure modes and disable path

Broken links, missing source revisions, untraceable status, a lost approval qualifier, or
a production claim supported only by offline tests fails documentation review. An
unavailable Issue/source is recorded as unverified with the last successful capture date;
it must not be assumed complete. Normative conflicts use the conflict register and a
separate change, with only the affected capability blocked as required by its sources.
Revert an incorrect documentation implementation or correct it through review; a
documentation revert cannot change running controls, permissions, or approval history.

## Security, privacy, and data lifecycle

Use public-safe control metadata only. No audio, payload, credential, identity data,
signed locator, provider identifier, secret value, or unredacted operational output is
stored in the index/evidence. Restricted evidence is represented by its allowed opaque
reference and scope, never copied. External reference expression and research reports
are not requirements inputs. The index grants no new access or processing purpose.

## Acceptance criteria

- [ ] Every covered requirement has the complete record fields above; stable source IDs
  are accounted for without duplicate primary definitions or silently discarded controls.
- [ ] Every ambiguous/conflicting definition is recorded with exact sources, affected
  capability, and separate resolution owner; no normative source was rewritten.
- [ ] Documentation, offline, runtime, hardware, provider, governance, and external
  permission evidence remain distinct, scoped, dated, and traceable.
- [ ] Merged artifacts, proposed ADR/risk records, unimplemented controls, historical
  evidence, missing permissions, and pending owner decisions remain truthfully labelled.
- [ ] Stage review proves production-only gates do not block the local synthetic #9/#11
  path while universal invariants and all applicable real-input gates remain intact.
- [ ] README reports merged #1/#3/#4 scope and unimplemented business/deployment scope;
  README and roadmap link the index and accurately describe the local-first sequence.
- [ ] Roadmap's direct edges match a dated GitHub audit; #27/#28/#29 responsibilities
  and #31's pending-only status are explicit without new implied approval.
- [ ] Link/section, stable-ID, dependency, status, scope, and whitespace audits plus
  repository deterministic checks pass with exact commands/results in `evidence.md`.
