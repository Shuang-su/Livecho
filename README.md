# Livecho

Livecho is an experimental, distributed real-time captioning system for public live
streams. A trusted cloud service ingests one stream, while invited community workers
perform speech recognition and a public web client renders the resulting timeline.

At the 2026-10-02 source baseline, the merged repository contains the engineering
foundation (#1), Alpha boundary specification and supporting records (#2), protocol v1
with deterministic Python/TypeScript compatibility verification (#3), and an offline,
fail-closed Railway skeleton (#4). The business runtime chain and live provider
environments are not established. Production traffic remains disabled.

The next product path is controlled memory-only synthetic audio (#8), a synthetic
single-worker path (#5/#6), the short local caption integration (#9), and its
caption/session-status Web companion (#11). Platform ingest (#7) follows the audio
pipeline; danmaku/Super Chat display has its own #10/#29 path. Each implementation
needs its accepted artifacts and scoped verification. Merged #5/#8 specifications
do not establish a running benchmark or audio pipeline.

See the [requirements and evidence index](docs/requirements-index.md) for source
authority, current evidence and capability-specific blockers, and the
[roadmap](docs/roadmap.md) for the dated direct dependency graph.

## Alpha boundaries

- One operator-selected public and free Bilibili room.
- One cloud ingest, invite-only Apple Silicon/MLX workers, and public live Web UI. Real
  audio remains disabled for community workers until the named rights and residual-risk
  gates are approved; synthetic protocol work may proceed.
- Captions, danmaku, Super Chat, and live-status events are restricted by default and may
  be retained only after the source-specific policy and Issue 16 deletion gates pass;
  audio is never persisted.
- CUDA is mock/contract-only during Alpha. Mac native UI and historical crawling are later
  milestones.

Public availability does not grant redistribution rights. Production ingest remains
disabled until the repository owner completes the current platform-policy and rights
review described in the change artifacts.

## Architecture and safety records

- [Alpha modular-monolith ADR](docs/architecture/adr/0001-alpha-modular-monolith.md)
- [Threat model and residual-risk register](docs/security/alpha-threat-model.md)
- [Data lifecycle and deletion rules](docs/security/data-lifecycle-and-deletion.md)
- [Bilibili public-ingest policy](docs/policy/bilibili-public-ingest.md)
- [Independent implementation and license isolation](docs/policy/independent-implementation.md)
- [Incident disable and recovery runbook](docs/operations/incident-disable-and-recovery.md)
- [Railway deployment, rollback, and destruction contract](docs/operations/railway-deployment.md)
- [Railway secret and managed-reference inventory](docs/operations/railway-secrets.md)

These records define constraints and later-Issue verification ownership; they do not
claim that a runtime control has already been implemented. The Railway records are
repository-only, fail-closed contracts; they do not mean that any Railway environment,
resource, provider control, or production deployment exists.

## Development

Prerequisites are Python 3.12,
[uv 0.12.1](https://docs.astral.sh/uv/getting-started/installation/), Node.js 22, and pnpm
11. The repository requires that exact uv release, so project commands fail before
dependency resolution when a different uv version is installed.

```sh
make bootstrap
make verify
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) before proposing a
change. Every implementation is linked to a GitHub Issue and versioned intent, spec,
plan, and evidence artifacts.

## License

[MIT](LICENSE). Dependencies and reference projects retain their own licenses; AGPL
source is not copied into this repository.
