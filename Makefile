.PHONY: bootstrap build dev lint test typecheck verify artifacts protocol-generate protocol-check

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

protocol-generate:
	uv run python tools/protocol_codegen.py

protocol-check:
	uv run python tools/protocol_codegen.py --check

verify: lint typecheck test artifacts protocol-check build
