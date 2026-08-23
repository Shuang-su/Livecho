# Independent implementation and license isolation

This policy implements the Issue #2 provenance and clean-room boundary. It is an
engineering control based on observed upstream notices and repository metadata, not a
legal conclusion about copyright scope, license compatibility, or any party's rights.
Questions that require such a conclusion must be escalated for independent review; an
uncertain result remains reference-only.

## Current decision

`LIC-DEC-001` permits no upstream copying in Issue #2. LAPLACE repositories classified
as AGPL, mixed, or unclear are reference-only. MIT-marked paths remain reference-only
until a later Issue identifies exact source blobs and destinations, receives approval,
and installs the required notice mapping. Model weights and datasets are outside every
source-code decision below and require separate approval.

Reference-only means do not copy, translate, port, adapt, transcribe, or derive source,
tests, fixtures, schemas, protocol layouts, configuration, comments, documentation
text, examples, assets, or distinctive structure. Rewriting in another language or
asking a model to paraphrase prohibited material does not change that decision.

## Capture method and exposure boundary

The register was captured on 2026-08-24 from the official GitHub repositories and
GitHub API. Revisions are full Git commit IDs. `tree` and `blob` values are native Git
object IDs returned for that revision. `SHA-256` is calculated over the decoded bytes of
the named license file; it is not a Git object ID.

The Issue #2 documentation author inspected repository metadata, commit/tree IDs, path
names, and license files and received generated factual summaries of upstream README
material, including Chatterbox algorithm/source descriptions, event-bridge package or
behavior descriptions, and the `ws` rewrite relationship. The author did not directly
open an upstream README or open source, test, fixture, configuration, design-document,
or asset contents. Both direct metadata exposure and summarized README exposure are
recorded rather than treated as zero exposure. No upstream expression was copied into
these requirements.

## Immutable upstream register

### `laplace-live/chatterbox`

- Canonical repository: <https://github.com/laplace-live/chatterbox>
- Captured revision: [`f94778722948d1a4f13577b34dc8f9a3e3b3556b`](https://github.com/laplace-live/chatterbox/commit/f94778722948d1a4f13577b34dc8f9a3e3b3556b)
- Root tree: `e1ac4ba7cdccac3fd23ba23a59536bc0e49dc23f`

| Path scope | Path object | Nearest observed notice | License blob | License SHA-256 | Operational class |
| --- | --- | --- | --- | --- | --- |
| Entire repository, including `src/**`, tests, docs, configuration, and assets | root tree above; `src` tree `7fc6761a6d5f7bbeaa8cc7962e11d055508ca689` | root `LICENSE`, GNU AGPL v3 text | `0ad25db4bd1d86c452db3f9602ccdbe172438f52` | `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` | AGPL-marked; reference-only |

No Chatterbox source, test, fixture, schema, configuration, comment, documentation, or
asset is an implementation input for Livecho.

### `laplace-live/event-bridge`

- Canonical repository: <https://github.com/laplace-live/event-bridge>
- Captured revision: [`aacb93811896d895d51f6918035ff1622c978ac8`](https://github.com/laplace-live/event-bridge/commit/aacb93811896d895d51f6918035ff1622c978ac8)
- Root tree: `81a59a45596074b58098458ec0aa4839d0ab0ca8`
- Mixed-license manifest: `LICENSE.md`, blob
  `d9599c5eb35f30c71fea7833a17465470e8f0360`, SHA-256
  `4f33acb90e78d290bfc8d8748e5002d152ca8eebb4a60f16d575e8f989c4eab9`.

| Path scope | Path tree | Nearest observed notice | License blob / SHA-256 | Operational class |
| --- | --- | --- | --- | --- |
| `packages/sdk/**` | `76d76231bc17a07114cd7a286c4b21ec337b72d0` | `packages/sdk/LICENSE`, MIT, copyright 2025 LAPLACE Live! | `848c870b6209459cea1d624bbc66a4e9cb817204` / `baee476ac956af9886dfc3542c4cd719780d21a72dd5d2ee60392ffd121a90e1` | MIT-marked candidate; currently reference-only |
| `packages/server/**` | `00add602196df825bb57ce4a41608eccb8db0779` | `packages/server/LICENSE`, GNU AGPL v3 text | `0ad25db4bd1d86c452db3f9602ccdbe172438f52` / `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` | AGPL-marked; reference-only |
| `packages/server-bun/**` | `dfbda6107ddd601134899af3e948e57f4db60c64` | `packages/server-bun/LICENSE`, GNU AGPL v3 text | `0ad25db4bd1d86c452db3f9602ccdbe172438f52` / `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` | AGPL-marked; reference-only |
| `examples/cli-demo/**` | `c0eb2eada4573081f2172a1cbbd57ebf7564f3d3` | `examples/cli-demo/LICENSE`, GNU AGPL v3 text | `0ad25db4bd1d86c452db3f9602ccdbe172438f52` / `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` | AGPL-marked; reference-only |
| `examples/react-demo/**` | `85e271309bb1a3c66f39fd0da2039664fa44efd1` | local `LICENSE` contains GNU AGPL v3 text, but the root manifest does not map this path | `0ad25db4bd1d86c452db3f9602ccdbe172438f52` / `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef` | Mixed/inconsistent; reference-only |
| `examples/tui-demo/**` | `f0e9dd2ccbf466988d9bb68c23506753a28689e6` | no local license observed; root mixed manifest does not map this path | root manifest blob/SHA-256 above | Unclear; reference-only |
| Every other root/config/docs/example path | root tree above | root manifest declares a mixed repository but does not assign every path | root manifest blob/SHA-256 above | Mixed or unclear; reference-only |

The root manifest's package list and a nearby license file are recorded facts, not a
legal determination that an unlisted file inherits a particular license. Mixed is the
safe default whenever the path-to-notice chain is incomplete or inconsistent.

### `laplace-live/ws`

- Canonical repository: <https://github.com/laplace-live/ws>
- Captured revision: [`78ca9803b6e94f3f98b4c65fd7cbcc153bd4491a`](https://github.com/laplace-live/ws/commit/78ca9803b6e94f3f98b4c65fd7cbcc153bd4491a)
- Root tree: `82bd15a7ad5305ebf5832b5f9955698ae3964b26`

| Path scope | Path object | Nearest observed notice | License blob | License SHA-256 | Operational class |
| --- | --- | --- | --- | --- | --- |
| Entire repository, including `src/**`, tests, docs, and configuration | root tree above; `src` tree `083560988bec4b4ec1ca6811f73e670806b49506` | root `LICENSE`, MIT, copyright 2019 simon3000 | `978685c29b92653a699593ef2a1fbfd55ab04e85` | `9f2a81a2689954d05295ae12a21f4bd7a7cb690eedc48ba6b123c98529441296` | MIT-marked candidate; currently reference-only |

## Independently written requirements

`LIC-REQ-001` makes the accepted Livecho artifacts and primary vendor/standard
documentation the only requirements supplied to implementers. Upstream LAPLACE
behavior, layout, naming, examples, tests, and protocol choices are not requirements.

| Livecho area | Independent requirement | Allowed requirement sources | Owning Issue |
| --- | --- | --- | --- |
| Protocol envelope | Locally design a bounded, versioned message protocol with explicit identity, lease, ordering, replay, size, timeout, and compatibility behavior. Golden fixtures must be authored from that specification. | Issue #2 records, Issue #3 artifact, generally available standards | #3 |
| Bilibili adapter | Resolve one operator-selected canonical room through the separately approved official channel; fail closed on restrictions, schema/rate changes, redirects, or missing rights. | `bilibili-public-ingest.md`, current official Bilibili docs for the approved channel | #7 |
| Event normalization | Validate untrusted platform payloads and map only locally specified danmaku, SC, live-status, and business-event fields into Livecho-owned models. | Issue #2 records and locally written Issue #10 requirements | #10 |
| Backend/worker transport | Backend remains authoritative; workers receive only bounded protocol messages and an allowlisted model manifest and return untrusted transcript/health frames. No shell, code, container, or server-provided download URL exists. | Issue #2 records and locally written Issues #3/#14 requirements | #3, #14 |
| Audio handling | At most 30 seconds of bounded RAM under the accepted byte/process limits; no audio persistence, retry queue, logging, fixture, telemetry, or crash artifact. | Issue #2 records and official decoder/model API documentation | #8, #14, #15 |
| Browser surface | Render only approved normalized output as untrusted content; ordinary browser/API/cache paths never receive raw payloads or worker connectivity. | Issue #2 records and locally written web Issue artifacts | #11, #17 |

Requirements authors must cite the allowed source that supports each externally imposed
fact. They must not resolve an unanswered design question by inspecting a reference-only
repository. Product similarities that follow from public facts or common standards are
documented as such; this policy does not pronounce on their legal treatment.

## Author exposure and exclusion

Before receiving an implementation assignment, every human or agent author must append
an exposure record to that Issue's evidence containing:

- identity, role, module/path, and date;
- every upstream repository, revision, and material previously viewed, including model
  context, pasted snippets, screenshots, generated summaries, and prior contributions;
- whether source, tests, fixtures, schemas, configuration, comments, docs, or assets
  were exposed; and
- the resulting assignment decision and independent reviewer.

`LIC-EXP-ISSUE2` records that this document's author saw the three repositories' names,
commit/tree objects, path names, license text, and generated factual summaries of README
material, including Chatterbox algorithm/source descriptions, event-bridge package or
behavior descriptions, and the `ws` rewrite relationship. The author is excluded from
later implementation of corresponding ASR/audio behavior, event-bridge-like event or
transport behavior, and `ws`-like transport modules unless the independent-review
exception below is recorded before assignment. The author must not rely on remembered
upstream layout, names, or summaries in any Livecho work. Any future implementation
assignment still needs a fresh exposure declaration. No exposure declaration for
`@Shuang-su` or future implementers is inferred from owner approval; each must be
recorded before work begins.

An author materially exposed to reference-only expression must not implement the
corresponding behavior or module. The only exception is an independently recorded
license/legal review that concludes the documented exposure was limited to public
requirements or unprotectable facts; the implementation author still receives only the
independently written requirement. Silence, memory loss, an agent context reset, or a
claim that the implementation was typed from scratch is not an exception.

## Reviewer separation and similarity response

The independent requirements author and implementation author must not inspect
reference-only material. A different post-implementation reviewer may inspect the
pinned upstream material solely to perform provenance, dependency, and similarity
review. That reviewer must not patch the implementation, paste upstream passages,
describe distinctive implementation details, or otherwise relay expression to the
author.

The reviewer records only the compared revisions/paths, tools and thresholds, result,
and any quarantined Livecho path. If material similarity is suspected, the pull request
stops; the affected work is removed or quarantined, the author is excluded, and a new
implementation is produced from `LIC-REQ-001` by an unexposed author. No finding is
waived merely to keep a deadline, and no review claims a definitive legal conclusion.

## MIT notice mapping

An MIT marker does not authorize an untracked copy. Before copying an exact file or a
substantial portion, a later pull request must replace the candidate row with a
file-level mapping: upstream repository/revision/path/blob, Livecho destination, copied
scope, copyright holder, full notice destination, approving reviewer, and verification.
The copyright and permission notice must accompany every copy or substantial portion.

| Candidate source | Current selected source blob | Livecho destination | Required notice destination | Decision |
| --- | --- | --- | --- | --- |
| `event-bridge@aacb93811896d895d51f6918035ff1622c978ac8:packages/sdk/**` | None; package tree only, no file selected | None | `docs/third-party-notices/event-bridge-sdk-MIT.txt` does not exist | Copy prohibited; reference-only |
| `ws@78ca9803b6e94f3f98b4c65fd7cbcc153bd4491a:**` | None; repository tree only, no file selected | None | `docs/third-party-notices/laplace-ws-MIT.txt` does not exist | Copy prohibited; reference-only |

The Livecho root `LICENSE` is not a substitute for either upstream notice. Adding a
dependency instead of copying code still requires its package lock, license inventory,
and distribution obligations to be reviewed. This Issue creates no notice file because
it copies no upstream material.

## Models, datasets, and generated material

Model code, weights, tokenizer/vocabulary files, datasets, prompts, generated fixtures,
and output-use terms are separate artifacts. A source-code license does not approve
them. Each requires an immutable version/digest, provenance, license and use scope,
distribution/hosting constraints, privacy/data basis, notice requirements, and owner
approval. Missing or conflicting evidence excludes the artifact from the allowlisted
model manifest.

Generated code or requirements must disclose all source context. A model cannot be used
to launder reference-only material: prompts, retrieval indexes, fine-tunes, or context
containing prohibited expression make the output tainted for the corresponding module
until independent review resolves it.

## Pull-request gate

Every later implementation pull request touching a related area must prove:

1. its intent/spec/plan were accepted before implementation;
2. implementer exposure records and assignment decisions predate the code;
3. requirements trace only to `LIC-REQ-001` sources;
4. no AGPL/mixed/unclear material, hidden generated context, or upstream-derived fixture
   entered the repository;
5. each MIT copy, if any, has an exact blob-to-destination notice mapping;
6. dependencies, models, datasets, and assets have separate immutable provenance; and
7. an isolated post-implementation reviewer records the pinned comparison and result.

Any missing record, path-level ambiguity, unexpected matching fragment, or unapproved
notice obligation blocks merge and release. The safe response is independent
reimplementation or removal, not a blanket assertion that the projects merely share an
idea.
