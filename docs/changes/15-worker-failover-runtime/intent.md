# Intent: Consume long-session rotation in the worker and viewer runtime

## Issue and owner

- GitHub Issue [#15](https://github.com/Shuang-su/Livecho/issues/15)
- Owner @Shuang-su
- Proposed. The gateway contract, its implementation and this consumer
  contract must be accepted before the application integration starts.

## User request

“继续让 Claude Code 推进多 worker 阶段，先解决 #62 的设备持钥证明与连接绑定，再把 #27 的轮换和重同步接入运行时。”

## Deliverable

For one synthetic session, select one compatible primary from up to three
invited and checked worker connections. Keep compatible standby workers
available without giving them audio. When the active lease is lost or
replaced, retire the old epoch, issue a bounded successor lease, and tell
viewers to resume from the new cursor. Report the gap and the actual time
to the successor's first accepted final.

The existing #27 protocol contract owns epochs, sequence and media
continuity. Consume that contract in the application through
`Minor1SessionRuntime` and its typed notices. The #9 short fixture's minor-0
transport remains a separate path.

## Boundaries

Synthetic source only. Use the approved model tuple, in-memory audio budgets,
one active lease, and the #13/#14 verified connection. Eligibility, health,
lease ownership, and accepted work are separate. The pilot does not need
public registration, persistence, a production source, or a shared scheduler
service. Genuine MLX-qualified scheduling evidence still depends on #5.
