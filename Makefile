.PHONY: bootstrap build dev lint test typecheck verify artifacts protocol-generate protocol-check web-check local-vertical-check local-vertical-demo asr-benchmark-check audio-check audio-runtime-check worker-check railway-check railway-start-web railway-start-backend railway-run-maintenance railway-migrate

bootstrap:
	uv sync --all-groups --frozen
	pnpm install --frozen-lockfile --ignore-scripts

build:
	pnpm build

dev:
	@echo "No runtime services exist in M0. Add service-specific dev commands with their Issue."

lint:
	uv run ruff check .
	uv run ruff format --check .
	pnpm lint

test:
	uv run pytest -q -m "not stress"
	pnpm test

typecheck:
	uv run mypy
	pnpm typecheck

artifacts:
	uv run python tools/check_change_artifacts.py

protocol-generate:
	uv run python tools/protocol_codegen.py

protocol-check:
	uv run python tools/protocol_codegen.py --check

web-check:
	pnpm --filter @livecho/web lint
	pnpm --filter @livecho/web typecheck
	pnpm --filter @livecho/web test
	pnpm --filter @livecho/web build
	pnpm --filter @livecho/web test:stress
	pnpm --filter @livecho/web test:e2e

railway-check:
	pnpm --filter @livecho/railway-config lint
	pnpm --filter @livecho/railway-config typecheck
	pnpm --filter @livecho/railway-config test
	pnpm --filter @livecho/railway-config build

railway-start-web:
	@echo "Web runtime is not implemented; Issue #11 owns this entry point." >&2
	@false

local-vertical-check:
	uv run pytest -q tests/local_vertical

local-vertical-demo:
	PYTHONPATH=packages/protocol/python:services/backend/src uv run python -m livecho_backend.local_vertical --segments 2

asr-benchmark-check:
	uv run ruff check tools/asr_benchmark tests/asr_benchmark
	uv run ruff format --check tools/asr_benchmark tests/asr_benchmark
	uv run mypy tools/asr_benchmark tests/asr_benchmark
	uv run pytest -q tests/asr_benchmark

audio-check:
	uv run pytest -q tests/audio
	@echo "Audio control checks only: trusted FFmpeg/host acceptance remains pending."

audio-runtime-check:
	PYTHONPATH=packages/protocol/python:services/backend/src uv run python -m livecho_backend.audio.preflight

worker-check:
	uv run pytest -q tests/worker
	@echo "Worker fixture/contract checks only: real MLX/host acceptance remains pending."

railway-start-backend:
	@echo "Backend runtime is not implemented; Issue #9 owns this entry point." >&2
	@false

railway-run-maintenance:
	@echo "No approved maintenance operation is installed." >&2
	@false

railway-migrate:
	@if [ -L db ] || { [ -e db ] && [ ! -d db ]; }; then echo "db must be a real, non-symlink directory when present." >&2; exit 1; fi
	@if [ -L db/migrations ] || [ -e db/migrations ]; then echo "db/migrations exists; the Issue #4 no-schema guard refuses to run." >&2; exit 1; fi
	@echo "NO_MIGRATIONS"

verify: lint typecheck test artifacts protocol-check build
