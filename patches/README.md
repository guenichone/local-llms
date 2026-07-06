# Custom Patches for Local LLM Setup

## files modified outside this repo

### free-claude-code (fcc) — uv tool install

| File | Change |
|---|---|
| `providers/llamacpp/client.py` | Added `postprocessors=(_ensure_min_max_tokens,)` to enforce `max_tokens >= 8192` for Ornith (reasoning model consumes tokens on `<think>` blocks) |
| `cli/claude_env.py` | `CLAUDE_CODE_AUTO_COMPACT_WINDOW` changed from `190000` to `180000` to match 200K context limit |
| `api/web_tools/request.py` | Added `effective_web_tool_name()` and modified `is_web_server_tool_request()` to auto-intercept `web_search`/`web_fetch` when `FCC_AUTO_INTERCEPT_WEB_TOOLS=true` |
| `api/web_tools/streaming.py` | Changed `forced_server_tool_name` → `effective_web_tool_name` so auto-intercepted requests use the first listed web tool |

**Critical:** `LLAMACPP_BASE_URL` must include `/v1` suffix. fcc's Anthropic transport appends `/messages` to the base URL:
- `http://127.0.0.1:8082/v1` → `http://127.0.0.1:8082/v1/messages` ✓
- `http://127.0.0.1:8082` → `http://127.0.0.1:8082/messages` ✗ (404)

Kill old `fcc-server` process before restarting to pick up config changes.

**To re-apply after fcc upgrade:**
```bash
./patches/reapply.sh
```

Or manually:
```bash
SITE=$(python -c "import providers.llamacpp; print(__import__('providers.llamacpp').__file__)")
SITE_DIR=$(dirname "$(dirname "$SITE")")
cp patches/fcc/llamacpp_client.py $SITE_DIR/providers/llamacpp/client.py
cp patches/fcc/claude_env.py $SITE_DIR/cli/claude_env.py
cp patches/fcc/request.py $SITE_DIR/api/web_tools/request.py
cp patches/fcc/streaming.py $SITE_DIR/api/web_tools/streaming.py
```

### shell config — ~/.zshrc.d/providers.zsh

Saved as `patches/providers.zsh`. Installed at `~/.zshrc.d/providers.zsh` (sourced from `.zshrc`).

Sets `MODEL="llamacpp/ornith-1.0-9b-Q5_K_M.gguf"` and `LLAMACPP_BASE_URL="http://127.0.0.1:8082/v1"` for fcc-server.
