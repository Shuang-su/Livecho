# Evidence: Minor-1 scheduling runtime

## User requests

1. “livecho项目也是 codex://threads/01a219b4-41a0-7743-ac04-4c591fce7b9a”
2. “对整体重新规划”
3. “Please implement the plan.”
4. “继续让 Claude Code 推进多 worker 阶段，先解决 #62 的设备持钥证明与连接绑定，再把 #27 的轮换和重同步接入运行时。”
5. “把 #62 的本地修订推上去，审查和 CI 通过后合并。然后继续让 Claude Code 实现网关，把 #27 的轮换和重同步接到调度器和字幕页，跑通 #15 的三 worker 故障切换验收。”
6. “授权” replies to the separate request to open and merge the #15
   specification PR after review and CI pass.

## Implementation assignment — 2026-11-27

- The user authorized opening and merging the separate #15 artifacts PR.
  PR #63 passed current-head review and Verify and merged as `95885aa`.
- This local implementation starts from that approved contract and stacks
  the prior #27 runtime and the verified #14 gateway. The local dependency
  parent for the #15-only diff is `7acf5ea`.
- Claude Code is assigned the minor-1 caption client. Codex is assigned
  scheduler, viewer fan-out, integration verification and independent
  review. Inputs are Livecho's accepted specifications, source and tests.
  No reference-project materials are implementation inputs. The integration
  remains a synthetic loopback exercise.

## Implementation and acceptance

- The isolated gateway continues to use #14 proof-bound worker admission.
  The scheduler admits up to three minor-1 sockets and uses fresh, trusted
  synthetic measurements for candidate ranking. Only its active lease
  accepts PCM or contributes results.
- A non-resumed promotion fences the previous lease, applies the #27
  transition, queues viewer resync independently of viewer I/O, and grants
  the successor. Upgrade-authenticated exact transfers keep the current
  lease and epoch when accepted before retirement.
- The failover caption build offers both minors with
  `VITE_LIVECHO_VIEWER_MINOR_1=1`. On a valid resync, the page clears old
  display and delay state and accepts the next event on the same WebSocket.
  On fresh admission while a partial is open, the fixture retries at a
  revision boundary. Expired or unknown cursors receive the #27 resync
  reason and current live cursor with no replay.
- Claude Code (Opus 5.5) implemented the gateway wire adapter and the caption
  protocol and session changes. Codex integrated identity proof, scheduling,
  viewer fan-out, compatibility fixes and tests.

### WSS and browser observations

| Scenario | Accepted heartbeat to successor final | Fault to viewer resync | Fault to successor lease | Resync to final |
| --- | ---: | ---: | ---: | ---: |
| Primary disconnect | 47.7 ms | 1.9 ms | 2.0 ms | 27.8 ms |
| Primary expiry with both browser viewports | 95.5 ms | 1.6 ms | 1.8 ms | 39.2 ms |

These are local monotonic timings. The fixture advanced its scheduler clock
by 2 seconds for the expiry case. Both scenarios discarded the previous
partial, skipped 40 ms from the retired PCM cursor to the successor's live
input, and accepted the first successor result as epoch 2, sequence 1.
The stalled viewer's send was cancelled independently. A further disconnect
promoted the third worker to epoch 3. Standbys got no pre-promotion PCM.
Exact viewer resume avoided a gap, while expired, rotated and unknown
cursors got the corresponding resync without replay. The viewer queue
allows 32 control frames and 256 KiB per connection and up to 20
connections, with a 500 ms send deadline.

The loopback browser ran Chromium at 1280 × 800 and 390 × 844 with a fresh
context. Each viewport saw the partial, set a 5,000 ms delay, saw it reset
to zero on the original socket at rotation, and rendered the successor
final. The PWA service worker was disabled in this synthetic TLS harness.

The scheduler test seeds 4,095 valid worker and viewer identities through
the protocol owner, then runs 4,096 and 4,097 through WSS. This tests the
transport boundary without pretending a 20-second rate-limited lease can
carry that many frames. The protocol suite tests capacity in each domain
independently and on successive epochs, tombstone eviction, and minor 0.

| Command | Observed result |
| --- | --- |
| `uv run pytest -q -s tests/worker_failover tests/worker_gateway tests/protocol/test_long_session.py tests/protocol/test_long_session_runtime.py` | Exit 0, 39 passed. |
| `VITE_LIVECHO_VIEWER_MINOR_1=1 pnpm --filter @livecho/web build` | Exit 0. |
| `LIVECHO_FAILOVER_BROWSER=1 uv run pytest -q -s --tb=short tests/worker_failover/test_failover.py -k three_worker_live_failover` | Exit 0, both scenarios passed, with Chromium in the expiry case. |
| `LIVECHO_FAILOVER_BROWSER=1 uv run pytest -q -s --tb=short tests/worker_failover tests/worker_gateway tests/protocol/test_long_session.py tests/protocol/test_long_session_runtime.py` | Exit 0, post-review targeted run with Chromium, 42 passed. |
| `LIVECHO_BASE_SHA=7acf5ea88daa833ccec95835a6f49bab4542f1bf make verify` | Exit 0 at implementation checkpoint `5d5b25b`. Ruff, mypy, 1,033 Python tests (1 stress case excluded), 431 Vitest cases, artifact and schema checks, and production build passed. |
| `pnpm --filter @livecho/protocol build && pnpm --filter @livecho/web test:e2e` | Exit 0, all 12 original minor-0 Chromium tests passed. |

### Independent runtime review

The reviewer identified five boundary conditions on `5d5b25b`. At expiry
the old connection now receives a bounded notice and releases its admission
slot. A cancelled lease send fences and detaches the selected worker before
selection proceeds. Eligibility is sampled after Welcome at lease issue, and
a blocked PCM send is capped by the remaining lease lifetime. A viewer that
needs a gap waits for a bounded clean revision boundary before registering
its live cursor. The post-review run exercised socket re-admission,
cancellation, stale observations, pending PCM, and a stale cursor while
old partials were open.

## Historical artifact approval and exposure

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

## Scope and remaining gates

- [PR #62](https://github.com/Shuang-su/Livecho/pull/62) merged the gateway
  documentation and its proof-binding revision at `63783a5`. The gateway
  implementation and this consumer implementation are separate changes.
- [Issue #27](https://github.com/Shuang-su/Livecho/issues/27) explicitly
  reserves gateway, scheduler, worker and viewer integration for their
  owning changes. The protocol adapter being validated locally only
  prepares that handoff.
- The lease remains 20 seconds and immutable. Fault recovery is verified
  with in-memory synthetic PCM, injected observations and protocol peers.
  A healthy continuation policy and its gap budget, real worker hosts and
  ASR, and the eight-hour run remain open. Production is not part of this
  acceptance.

## Historical artifact verification

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
