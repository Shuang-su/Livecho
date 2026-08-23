# Livecho

Livecho is an experimental, distributed real-time captioning system for public live
streams. A trusted cloud service ingests one stream, while invited community workers
perform speech recognition and a public web client renders the resulting timeline.

The repository is currently establishing its engineering and review foundation. No
runtime product code is included in the first pull request.

## Alpha boundaries

- One operator-selected public and free Bilibili room.
- One cloud ingest, invite-only Apple Silicon/MLX workers, and public live Web UI.
- Captions, danmaku, Super Chat, and live-status events are retained; audio is never
  persisted.
- CUDA is contract-only during Alpha. Mac native UI and historical crawling are later
  milestones.

Public availability does not grant redistribution rights. Production ingest remains
disabled until the repository owner completes the current platform-policy and rights
review described in the change artifacts.

## Development

Prerequisites are Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js 22, and pnpm 11.

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
