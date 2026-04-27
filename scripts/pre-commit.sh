#!/usr/bin/env bash
# Pre-commit hook: smoke-test that the frontend boots and the quiz flow works.
#
# Skips if no relevant files are staged, so README-only commits stay fast.
# Activates a local .venv if present.
#
# To install: ./scripts/install-git-hooks.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Only run when files that could affect the running app are staged.
RELEVANT_PATTERN='^(frontend/|backend/|tests/|conftest\.py$|requirements\.txt$|pytest\.ini$)'
CHANGED="$(git diff --cached --name-only --diff-filter=ACMR | grep -E "$RELEVANT_PATTERN" || true)"

if [ -z "$CHANGED" ]; then
  echo "[pre-commit] no frontend/backend/test changes staged — skipping integration test"
  exit 0
fi

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "[pre-commit] running tests/test_integration.py (boots Next.js + drives the full quiz flow)"
pytest tests/test_integration.py -q
