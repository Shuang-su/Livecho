# Evidence: Minor-1 scheduling runtime proposal

## Artifact approval and exposure

- Proposed. Owner merge and implementation evidence pending.
- Base `63783a514002cfbfa43f6ac9ef3962a8975ebd50`, branch
  `codex/issue-15-failover-artifacts`. This publication follows explicit
  owner authorization to open and merge the documentation PR after review
  and CI pass.
- 2026-11-27: Codex documented the application integration from the user's
  request, Livecho's own #13/#14/#27 contracts, the current #15 issue and
  its owner confirmation. Claude Code Opus 5.5 independently analyzed the #27
  protocol-runtime connection from first-party source fragments. This
  requirements assignment does not itself appoint a future app implementer.
  Reference-project expression, code, fixtures and assets were not inputs.

## Existing gates

- [PR #62](https://github.com/Shuang-su/Livecho/pull/62) merged the gateway
  documentation and its proof-binding revision at `63783a5`. The gateway
  implementation and this consumer implementation are separate changes.
- [Issue #27](https://github.com/Shuang-su/Livecho/issues/27) explicitly
  reserves gateway, scheduler, worker and viewer integration for their
  owning changes. The protocol adapter being validated locally only
  prepares that handoff.
- Current gateway drafts use one 20-second lease and no healthy successor.
  The app needs an approved handoff policy and measured gap behavior before
  long-running operational acceptance.

## Verification

| Command | Observed result on 2026-11-27 |
| --- | --- |
| `python3 -B tools/check_change_artifacts.py` | Exit 0, `change artifacts: ok`. |
| `git diff --check origin/main...HEAD` | Exit 0, no whitespace errors. |
| `git diff --cached --check` | Exit 0 on the staged evidence revision. |
| `gh run view 45960338115 -R Shuang-su/Livecho --json headSha,conclusion` | `success` for `78ecdef`, the original PR head before this evidence revision. |

The exact local path and Markdown link check used:

```sh
python3 -B - <<'PY'
from pathlib import Path
import re

root = Path("docs/changes/15-worker-failover-runtime")
files = list(root.glob("*.md"))
assert {p.name for p in files} == {"intent.md", "spec.md", "plan.md", "evidence.md"}
relative_count = 0
for file in files:
    for target in re.findall(r"\]\(([^)]+)\)", file.read_text()):
        if "://" in target or target.startswith("#"):
            continue
        assert (file.parent / target.split("#", 1)[0]).resolve().is_file()
        relative_count += 1
print(f"{len(files)} required artifacts, {relative_count} relative links verified")
PY
```

It exited 0 with `4 required artifacts, 0 relative links verified`. No
socket, device, three-worker, hardware, or production result is asserted by
this draft.
