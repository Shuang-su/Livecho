# Security policy

Livecho is pre-Alpha and does not yet accept production traffic.

Please report vulnerabilities privately through GitHub's security advisory flow. Do
not include stream credentials, private URLs, user identifiers, archived event payloads,
or audio samples in public issues.

The non-negotiable security invariants are documented in [AGENTS.md](AGENTS.md). The
current proposed design records are:

- [Alpha modular-monolith ADR](docs/architecture/adr/0001-alpha-modular-monolith.md)
- [Alpha threat model and residual-risk register](docs/security/alpha-threat-model.md)
- [Data lifecycle and deletion rules](docs/security/data-lifecycle-and-deletion.md)
- [Incident disable and recovery runbook](docs/operations/incident-disable-and-recovery.md)
- [Public-ingest policy and current production gate](docs/policy/bilibili-public-ingest.md)
- [Independent implementation and license isolation](docs/policy/independent-implementation.md)

Production ingest is globally disabled. Missing or stale policy/rights evidence, an
unaccepted Critical/High residual risk, or unreconciled safety/deletion recovery state
keeps it disabled.
