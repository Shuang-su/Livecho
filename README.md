# Livecho

Livecho is an experimental, distributed real-time captioning system for public live
streams. A trusted cloud service ingests one stream, while invited community workers
perform speech recognition and a public web client renders the resulting timeline.

At the 2026-11-21 source baseline (`f62951f`), the merged repository contains:

- Engineering foundation (#1), Alpha boundary records (#2), protocol v1 with
  deterministic Python/TypeScript verification (#3), and an offline fail-closed
  Railway skeleton (#4).
- **Fixture/CI-gated M1 slices** (not real product acceptance): #5 ASR control plane,
  #6 worker fixture CLI, #7 ingest fixtures, #8 audio control plane, #9
  `fixture_timeline` local vertical, #10 offline event normalize, #11 caption PWA
  with Node-double and Python cross-stack E2E ([#44](https://github.com/Shuang-su/Livecho/pull/44)–[#54](https://github.com/Shuang-su/Livecho/pull/54)).
- **Offline-only M2 slices** (not real product acceptance): #27 protocol minor 1 for
  long-session epoch rotation and viewer resynchronization, in the protocol package
  only ([#58](https://github.com/Shuang-su/Livecho/pull/58)); #12 invite-only
  magic-link authentication and role matrix on a process-local memory adapter, not
  mounted by any other application and with mail off
  ([#59](https://github.com/Shuang-su/Livecho/pull/59)).

The business runtime chain that performs real ASR, live Bilibili acquisition, wire
danmaku/SC publication, invited login with delivered mail and durable accounts, or
provider deployment is **not** established. Production traffic remains disabled. CUDA
remains mock/contract-only. Green CI and closed fixture Issues do not mean hardware,
rights, or live gates passed.

See the [requirements and evidence index](docs/requirements-index.md) for source
authority, evidence categories, and blockers, and the [roadmap](docs/roadmap.md) for
the dated direct dependency graph.

## Local synthetic caption path (fixture only)

```sh
# Python fixture_timeline (Issue #9) serving the built #11 shell:
make web-python-e2e
# Or manually:
#   PYTHONPATH=packages/protocol/python:services/backend/src \
#     uv run python -m livecho_backend.local_vertical --server-only --static-root apps/web/dist
# Node double alone (what make web-check uses):
pnpm --filter @livecho/web demo
```

`synthetic_mlx`, live ingest, wire publish, and raw archive flags stay closed.

## Alpha boundaries

- One operator-selected public and free Bilibili room.
- One cloud ingest, invite-only Apple Silicon/MLX workers, and public live Web UI. Real
  audio remains disabled for community workers until the named rights and residual-risk
  gates are approved; synthetic protocol and fixture work may proceed.
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
