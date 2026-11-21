# Alpha roadmap

Snapshot captured 2026-11-21 against `f62951f2b5a083610a92d155d28afa19e4159dbe`.
The previous snapshot was 2026-11-15 at `c8ee4a1`; this one adds the #12 and #27
merges ([#56][p56]–[#59][p59]).
GitHub Issues provide planning state and direct dependencies; accepted artifacts define
implementation authority. A closed Issue after a fixture/CI slice is **not** proof of
real ASR, live ingest, wire publication, or production readiness. The
[requirements index](requirements-index.md) separates these facts and their evidence.

## Local caption path

The short local **fixture** demonstration follows #8 control-plane audio contracts and
#5/#6 fixture worker gates into #9 `fixture_timeline`, then #11's caption/session-status
PWA (including Python cross-stack E2E via [#54](https://github.com/Shuang-su/Livecho/pull/54)).
#7 fixture ingest and #10 offline normalize landed as CI-safe slices; live channel
selection, rights, wire danmaku/SC (#29), and #16 archive remain separate.

Neither platform access nor #27/#28/#29/#30 completion is a new dependency for the short
#9/#11 synthetic fixture path. #9 stays on protocol minor 0; the merged #27 minor 1 is
not wired into it. Universal audio ephemerality, protocol validation, and
other applicable constraints still apply. Real MLX/`synthetic_mlx`, approved FFmpeg/host,
and live Bilibili remain blocked.

## Direct dependency snapshot

Every cell lists direct prerequisites only, captured from the owning Issue's `依赖`
section on 2026-11-21. Links resolve to exact Issues. Planning state is GitHub's current
state; “closed” after a fixture PR does not clear remaining hardware/rights rows in the
index.

| Issue | Planning state | Owned outcome | Direct prerequisites | Fixture/CI note |
| --- | --- | --- | --- | --- |
| [#1][i1] | closed | Repository and SDLC foundation | none | foundation merged |
| [#2][i2] | closed | Architecture, security and data/platform boundaries | [#1][i1] | docs; ADR/risks still Proposed |
| [#3][i3] | closed | Protocol v1 and cross-language contracts | [#1][i1], [#2][i2] | offline validators |
| [#4][i4] | closed | Offline Railway skeleton | [#1][i1], [#2][i2] | no live provider |
| [#5][i5] | closed | M3 Ultra MLX benchmark and model evidence | [#1][i1], [#2][i2] | control plane [#46][p46]; real MLX missing |
| [#6][i6] | closed | MLX CLI and synthetic worker path | [#3][i3], [#5][i5] | fixture CLI [#49][p49]; real run missing |
| [#7][i7] | closed | Eligible public/free room resolver | [#2][i2], [#3][i3], [#8][i8] | fixture SM [#51][p51]; live missing |
| [#8][i8] | closed | Supervised decoder and bounded memory audio | [#2][i2], [#3][i3] | control plane [#47][p47]; host missing |
| [#9][i9] | open | Short single-worker local caption integration | [#3][i3], [#6][i6], [#8][i8] | `fixture_timeline` [#45][p45]/[#54][p54]; MLX closed |
| [#10][i10] | closed | Normalize danmaku, SC and live status | [#2][i2], [#3][i3], [#7][i7] | offline normalize [#53][p53]; wire missing |
| [#11][i11] | open | First caption/session-status Web/PWA | [#3][i3], [#9][i9] | PWA [#44][p44] + Python E2E [#54][p54] |
| [#12][i12] | closed | Invite-only email authentication and roles | [#2][i2], [#4][i4] | memory-adapter auth [#59][p59]; mail, durable store, production missing |
| [#13][i13] | open | Invited worker enrollment, identity and statistics | [#3][i3], [#6][i6], [#12][i12] | not implemented; artifact PR [#60][p60] open, unmerged |
| [#14][i14] | open | Gateway, heartbeat and lease lifecycle | [#3][i3], [#13][i13] | not implemented |
| [#15][i15] | open | Scheduling and failover | [#5][i5], [#13][i13], [#14][i14], [#27][i27] | not implemented |
| [#16][i16] | open | Normalized history, encrypted raw archive and deletion | [#2][i2], [#4][i4], [#10][i10], [#12][i12] | not implemented |
| [#17][i17] | open | Invited history/statistics and operator/admin console | [#11][i11], [#12][i12], [#13][i13], [#16][i16] | not implemented |
| [#18][i18] | open | CUDA mock and cross-provider contracts | [#3][i3], [#6][i6], [#14][i14] | not implemented |
| [#19][i19] | open | Live deployment, recovery and Alpha acceptance | [#4][i4], [#7][i7], [#11][i11], [#15][i15], [#16][i16], [#17][i17], [#18][i18], [#27][i27], [#28][i28], [#29][i29] | not implemented |
| [#27][i27] | open | Long-session bounded state and resynchronization | [#3][i3] | protocol minor 1 [#58][p58]; runtime wiring missing |
| [#28][i28] | open | Real-input origin and capability negotiation | [#2][i2], [#3][i3] | not implemented |
| [#29][i29] | open | Independent danmaku/Super Chat Web delivery | [#10][i10], [#11][i11] | not implemented |
| [#30][i30] | open | Requirement/evidence navigation maintenance | [#2][i2], [#3][i3], [#4][i4] | this documentation |

[#31](https://github.com/Shuang-su/Livecho/issues/31) is open with the current title
“研究与设计提案：开放贡献闭环、可信统计及字幕体验”. Only title/state were inspected.
It is a pending proposal: no roles, enrollment, metrics, UI requirements, dependencies
or acceptance are inferred.

[#38](https://github.com/Shuang-su/Livecho/issues/38) is open with the current title
“架构提案：公开 Livecho 账号与自助设备的权限边界”. Only number/title/state were
inspected. It is listed the same way as #31: no account model, enrollment path,
dependency or acceptance is inferred, and it is not a row in the table above.

## Conditional capability gates

- Long-session scheduling/Alpha operation needs #27 lifecycle evidence. The offline
  minor-1 rotation contract is merged ([#58][p58]); no consumer is wired to it and no
  long-running session has been exercised, so indefinite sessions are not established.
- Invited login needs more than the merged #12 memory adapter ([#59][p59]): mail
  delivery, a durable identity store, restore rejection of old credentials and sealed
  secrets have no evidence. Public live viewing stays anonymous.
- Real input needs #28 negotiation and the existing exact-channel, source, rights,
  worker-disclosure, individual-risk and safety gates. A real-input demo is real input.
  Local synthetic/fixture work retains the synthetic-only v1 contract.
- Persistence, history, identity and distributed scheduling need their owning Issues'
  authorization, deletion, recovery and operational evidence. These gates do not become
  prerequisites for unrelated local fixture work.
- Provider staging/production needs actual environment evidence. The offline #4
  skeleton does not establish resources, usable credentials, deployed health checks,
  maintenance fencing or provider deletion guarantees. Production remains off.
- CUDA remains mock/contract-only; real hardware behavior needs a later approved Issue.
- Real MLX ASR needs #5 ADR + trusted M3 Ultra evidence before #6/#9 can leave fixture
  mode; #8 host/FFmpeg evidence is required before real audio budgets clear.

No direct-edge discrepancy was found against the accepted #30 dependency snapshot on
2026-11-21. The one planning-state change since 2026-11-15 is #12, which GitHub closed
on 2026-11-18. Changes to an owning Issue's dependencies, artifacts, evidence or approvals
trigger a review of this table, the index and README through normal PR review. An Issue
edit cannot override an accepted contract. Exact snapshot/audit commands are retained in
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
[p44]: https://github.com/Shuang-su/Livecho/pull/44
[p45]: https://github.com/Shuang-su/Livecho/pull/45
[p46]: https://github.com/Shuang-su/Livecho/pull/46
[p47]: https://github.com/Shuang-su/Livecho/pull/47
[p49]: https://github.com/Shuang-su/Livecho/pull/49
[p51]: https://github.com/Shuang-su/Livecho/pull/51
[p53]: https://github.com/Shuang-su/Livecho/pull/53
[p54]: https://github.com/Shuang-su/Livecho/pull/54
[p56]: https://github.com/Shuang-su/Livecho/pull/56
[p58]: https://github.com/Shuang-su/Livecho/pull/58
[p59]: https://github.com/Shuang-su/Livecho/pull/59
[p60]: https://github.com/Shuang-su/Livecho/pull/60
