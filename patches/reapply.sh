#!/usr/bin/env bash
set -euo pipefail

# Re-apply custom patches after free-claude-code upgrade.
# Run from repo root: ./patches/reapply.sh

REPO="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Finding fcc site-packages..."
SITE=$(python -c "import providers.llamacpp; print(__import__('providers.llamacpp').__file__)" 2>/dev/null)
SITE_DIR=$(dirname "$(dirname "$SITE")")

if [ -z "$SITE_DIR" ] || [ ! -d "$SITE_DIR" ]; then
  echo "ERROR: Could not locate fcc site-packages" >&2
  exit 1
fi

echo "    Site: $SITE_DIR"

echo "==> Patching llamacpp client..."
cp "$REPO/patches/fcc/llamacpp_client.py" "$SITE_DIR/providers/llamacpp/client.py"
echo "    OK"

echo "==> Patching claude_env.py..."
cp "$REPO/patches/fcc/claude_env.py" "$SITE_DIR/cli/claude_env.py"
echo "    OK"

echo "==> Patching web_tools request.py (auto-intercept)..."
cp "$REPO/patches/fcc/request.py" "$SITE_DIR/api/web_tools/request.py"
echo "    OK"

echo "==> Patching web_tools streaming.py (auto-intercept)..."
cp "$REPO/patches/fcc/streaming.py" "$SITE_DIR/api/web_tools/streaming.py"
echo "    OK"

echo "==> Checking providers.zsh..."
if diff "$REPO/patches/providers.zsh" "$HOME/.zshrc.d/providers.zsh" >/dev/null 2>&1; then
  echo "    Already up-to-date"
else
  echo "    WARNING: ~/.zshrc.d/providers.zsh differs from saved copy"
  echo "    Compare: diff $REPO/patches/providers.zsh $HOME/.zshrc.d/providers.zsh"
fi

echo ""
echo "==> IMPORTANT: After restarting fcc-server, verify LLAMACPP_BASE_URL includes /v1:"
echo "    cat /proc/\$(pgrep -f fcc-server)/environ | tr '\\0' '\\n' | grep LLAMACPP"
echo "    Expected: LLAMACPP_BASE_URL=http://127.0.0.1:8082/v1"
echo "    Wrong:    LLAMACPP_BASE_URL=http://127.0.0.1:8082 (missing /v1 → 404)"
