# Alpha roadmap

Snapshot captured 2026-10-02 and rechecked 2026-10-03 (Asia/Shanghai), source baseline
`93d8b0a4b3e147ce0b7df903f118060117d56f0a`. GitHub Issues provide planning state and
direct dependencies; accepted artifacts define implementation authority. An open Issue
is not specification approval, and a closed Issue is not proof of a running service.
The [requirements index](requirements-index.md) separates these facts and their evidence.

## Local caption path

The first short local demonstration follows #8 controlled synthetic audio and #5/#6
synthetic worker work into #9, then #11's caption/session-status page. #7 platform ingest
follows #8; #10 normalized events and #29 danmaku/Super Chat display are a separate path.
Neither platform access nor #27/#28/#29/#30 completion is a new dependency for the short
#9/#11 synthetic path. Its own artifacts, audio ephemerality, protocol validation and
other applicable universal constraints still apply.

The #5 and #8 specifications are merged through PRs
[#33](https://github.com/Shuang-su/Livecho/pull/33) and
[#34](https://github.com/Shuang-su/Livecho/pull/34); runtime and hardware evidence remain
pending at this baseline. No model/audio download or production activation is authorized
by this roadmap.

## Direct dependency snapshot

Every cell lists direct prerequisites only, captured from the owning Issue's `依赖`
section. Links resolve to exact Issues. The list is not numeric execution order.

| Issue | Planning state | Owned outcome | Direct prerequisites |
| --- | --- | --- | --- |
| [#1][i1] | closed | Repository and SDLC foundation | none |
| [#2][i2] | closed | Architecture, security and data/platform boundaries | [#1][i1] |
| [#3][i3] | closed | Protocol v1 and cross-language contracts | [#1][i1], [#2][i2] |
| [#4][i4] | closed | Offline Railway skeleton | [#1][i1], [#2][i2] |
| [#5][i5] | open | M3 Ultra MLX benchmark and model evidence | [#1][i1], [#2][i2] |
| [#6][i6] | open | MLX CLI and synthetic worker path | [#3][i3], [#5][i5] |
| [#7][i7] | open | Eligible public/free room resolver | [#2][i2], [#3][i3], [#8][i8] |
| [#8][i8] | open | Supervised decoder and bounded memory audio | [#2][i2], [#3][i3] |
| [#9][i9] | open | Short single-worker local caption integration | [#3][i3], [#6][i6], [#8][i8] |
| [#10][i10] | open | Normalize danmaku, SC and live status | [#2][i2], [#3][i3], [#7][i7] |
| [#11][i11] | open | First caption/session-status Web/PWA | [#3][i3], [#9][i9] |
| [#12][i12] | open | Invite-only email authentication and roles | [#2][i2], [#4][i4] |
| [#13][i13] | open | Invited worker enrollment, identity and statistics | [#3][i3], [#6][i6], [#12][i12] |
| [#14][i14] | open | Gateway, heartbeat and lease lifecycle | [#3][i3], [#13][i13] |
| [#15][i15] | open | Scheduling and failover | [#5][i5], [#13][i13], [#14][i14], [#27][i27] |
| [#16][i16] | open | Normalized history, encrypted raw archive and deletion | [#2][i2], [#4][i4], [#10][i10], [#12][i12] |
| [#17][i17] | open | Invited history/statistics and operator/admin console | [#11][i11], [#12][i12], [#13][i13], [#16][i16] |
| [#18][i18] | open | CUDA mock and cross-provider contracts | [#3][i3], [#6][i6], [#14][i14] |
| [#19][i19] | open | Live deployment, recovery and Alpha acceptance | [#4][i4], [#7][i7], [#11][i11], [#15][i15], [#16][i16], [#17][i17], [#18][i18], [#27][i27], [#28][i28], [#29][i29] |
| [#27][i27] | open | Long-session bounded state and resynchronization | [#3][i3] |
| [#28][i28] | open | Real-input origin and capability negotiation | [#2][i2], [#3][i3] |
| [#29][i29] | open | Independent danmaku/Super Chat Web delivery | [#10][i10], [#11][i11] |
| [#30][i30] | open | Requirement/evidence navigation maintenance | [#2][i2], [#3][i3], [#4][i4] |

[#31](https://github.com/Shuang-su/Livecho/issues/31) is open with the current title
“研究与设计提案：开放贡献闭环、可信统计及字幕体验”. Only title/state were inspected.
It is a pending proposal: no roles, enrollment, metrics, UI requirements, dependencies
or acceptance are inferred. The title adds a proposal prefix to the shorter historical
title in #30's accepted artifacts; this is metadata drift, not accepted scope.

## Conditional capability gates

- Long-session scheduling/Alpha operation needs #27 lifecycle evidence; the existing
  bounded protocol contract does not establish indefinite sessions.
- Real input needs #28 negotiation and the existing exact-channel, source, rights,
  worker-disclosure, individual-risk and safety gates. A real-input demo is real input.
  Local synthetic work retains the synthetic-only v1 contract.
- Persistence, history, identity and distributed scheduling need their owning Issues'
  authorization, deletion, recovery and operational evidence. These gates do not become
  prerequisites for unrelated local synthetic work.
- Provider staging/production needs actual environment evidence. The offline #4
  skeleton does not establish resources, usable credentials, deployed health checks,
  maintenance fencing or provider deletion guarantees. Production remains off.
- CUDA remains mock/contract-only; real hardware behavior needs a later approved Issue.

No direct-edge discrepancy was found against the accepted #30 dependency snapshot.
Changes to an owning Issue's dependencies, artifacts, evidence or approvals trigger a
review of this table, the index and README through normal PR review. An Issue edit cannot
override an accepted contract. The exact snapshot/audit is retained in
[#30 evidence](changes/30-requirements-evidence-index/evidence.md).

[i1]: https://github.com/Shuang-su/Livecho/issues/1
[i2]: https://github.com/Shuang-su/Livecho/issues/2
[i3]: https://github.com/Shuang-su/Livecho/issues/3
[i4]: https://github.com/Shuang-su/Livecho/issues/4
[i5]: https://github.com/Shuang-su/Livecho/issues/5
[i6]: https://github.com/Shuang-su/Livecho/issues/6
[i7]: https://github.com/Shuang-su/Livecho/issues/7
[i8]: https://github.com/Shuang-su/Livecho/issues/8
[i9]: https://github.com/Shuang-su/Livecho/issues/9
[i10]: https://github.com/Shuang-su/Livecho/issues/10
[i11]: https://github.com/Shuang-su/Livecho/issues/11
[i12]: https://github.com/Shuang-su/Livecho/issues/12
[i13]: https://github.com/Shuang-su/Livecho/issues/13
[i14]: https://github.com/Shuang-su/Livecho/issues/14
[i15]: https://github.com/Shuang-su/Livecho/issues/15
[i16]: https://github.com/Shuang-su/Livecho/issues/16
[i17]: https://github.com/Shuang-su/Livecho/issues/17
[i18]: https://github.com/Shuang-su/Livecho/issues/18
[i19]: https://github.com/Shuang-su/Livecho/issues/19
[i27]: https://github.com/Shuang-su/Livecho/issues/27
[i28]: https://github.com/Shuang-su/Livecho/issues/28
[i29]: https://github.com/Shuang-su/Livecho/issues/29
[i30]: https://github.com/Shuang-su/Livecho/issues/30
