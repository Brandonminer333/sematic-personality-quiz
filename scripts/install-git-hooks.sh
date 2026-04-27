#!/usr/bin/env bash
# One-time installer: wires .git/hooks/pre-commit to scripts/pre-commit.sh.
#
# Usage: ./scripts/install-git-hooks.sh

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_PATH="$REPO_ROOT/.git/hooks/pre-commit"
SCRIPT_PATH="$REPO_ROOT/scripts/pre-commit.sh"

if [ ! -f "$SCRIPT_PATH" ]; then
  echo "error: $SCRIPT_PATH not found" >&2
  exit 1
fi

chmod +x "$SCRIPT_PATH"

cat > "$HOOK_PATH" <<'EOF'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/scripts/pre-commit.sh" "$@"
EOF
chmod +x "$HOOK_PATH"

echo "✓ pre-commit hook installed: $HOOK_PATH"
echo "  delegates to:                $SCRIPT_PATH"
echo
echo "Prerequisites (one-time):"
echo "  pip install -r requirements.txt"
echo "  playwright install chromium"
echo "  (cd frontend && npm install)"
