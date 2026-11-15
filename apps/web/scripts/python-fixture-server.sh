#!/usr/bin/env bash
# Start the real Issue #9 Python fixture_timeline server serving this package's
# production shell from dist/. Used by Playwright python-e2e only — not MLX.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DIST="${ROOT}/apps/web/dist"
export PYTHONPATH="${ROOT}/packages/protocol/python:${ROOT}/services/backend/src${PYTHONPATH:+:${PYTHONPATH}}"
exec uv run python -m livecho_backend.local_vertical \
  --server-only \
  --static-root "${DIST}" \
  "$@"
