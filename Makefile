.PHONY: bootstrap build dev lint test typecheck verify artifacts

bootstrap:
	uv sync --all-groups --frozen
	pnpm install --frozen-lockfile

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

verify: lint typecheck test artifacts build
