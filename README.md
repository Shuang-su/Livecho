# Livecho

Livecho is an experimental, distributed real-time captioning system for public live
streams. A trusted cloud service ingests one stream, while invited community workers
perform speech recognition and a public web client renders the resulting timeline.

The repository currently contains its engineering foundation, an accepted Alpha boundary
specification, and proposed supporting design records. It does not yet contain runtime
product code or accept production traffic.

## Alpha boundaries

- One operator-selected public and free Bilibili room.
- One cloud ingest, invite-only Apple Silicon/MLX workers, and public live Web UI. Real
  audio remains disabled for community workers until the named rights and residual-risk
  gates are approved; synthetic protocol work may proceed.
- Captions, danmaku, Super Chat, and live-status events are restricted by default and may
  be retained only after the source-specific policy and Issue 16 deletion gates pass;
  audio is never persisted.
- CUDA is contract-only during Alpha. Mac native UI and historical crawling are later
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

These records define constraints and later-Issue verification ownership; they do not
claim that a runtime control has already been implemented.

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
