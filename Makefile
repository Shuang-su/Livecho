.PHONY: bootstrap build dev lint test typecheck verify artifacts protocol-generate protocol-check railway-check railway-start-web railway-start-backend railway-run-maintenance railway-migrate

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
	uv run pytest -q
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

railway-check:
	pnpm --filter @livecho/railway-config lint
	pnpm --filter @livecho/railway-config typecheck
	pnpm --filter @livecho/railway-config test
	pnpm --filter @livecho/railway-config build

railway-start-web:
	@echo "Web runtime is not implemented; Issue #11 owns this entry point." >&2
	@false

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
