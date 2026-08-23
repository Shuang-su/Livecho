# Intent: establish the Livecho repository and AI-native SDLC foundation

## Issue and owner

- GitHub Issue: [#1](https://github.com/Shuang-su/Livecho/issues/1)
- Human owner: @Shuang-su
- Stage/area/risk: `stage:m0`, `area:repo`, `type:chore`, `risk:low`

## Problem

The GitHub repository is empty. There is no deterministic development entry point,
reviewable change record, CI contract, or durable guidance for human and AI contributors.
Starting product work in this state would make protocol, privacy, and operational choices
implicit and difficult to review.

## Desired outcome

Create a minimal monorepo foundation that makes every later change Issue-driven,
artifact-first, deterministic to verify, and explicitly human-gated. The first pull
request must be useful without implementing product behavior.

## Non-goals

- Runtime backend, Web client, ASR worker, Bilibili integration, persistence, or auth.
- Railway resources, production deployment, Codex Hooks, repository Skills, or agent
  evals.
- Automatic merging or deployment.

## Constraints and data impact

- Keep instructions concise enough for Codex's repository guidance chain.
- Pin the supported Python, Node, pnpm, and development dependency versions.
- Use MIT for original Livecho code and prohibit copying AGPL reference code.
- Data classification: none. No stream, user, worker, event, or audio data is processed.

## Success signal

A new contributor can clone the repository, run `make bootstrap && make verify`, copy a
complete change template, and understand the human approval boundary without private
context.

## Human decision

- Status: Approved for squash merge after required checks and review threads pass
- Approved by/date: @Shuang-su, 2026-08-24 (explicit merge authorization)
