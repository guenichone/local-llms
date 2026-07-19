# ── Provider Aliases ──────────────────────────────────────────────
# Source: ~/.zshrc.d/providers.zsh
# Requires: OPENROUTER_API_KEY in ~/Development/local-llms/.env

OR_PROXY_PORT="${OR_PROXY_PORT:-8099}"
OR_PROXY_SCRIPT="$HOME/Development/local-llms/.claude/or-proxy.mjs"
OR_ENV="$HOME/Development/local-llms/.env"

# ── Claude Code via OpenRouter ────────────────────────────────────
claude-or() {
  local model="${1:-claude-opus-4-8}"
  # Start proxy if not running
  if ! lsof -i :$OR_PROXY_PORT >/dev/null 2>&1; then
    nohup node "$OR_PROXY_SCRIPT" > /tmp/or-proxy.log 2>&1 & disown
    sleep 1
  fi
  # Read key once
  local key
  key=$(grep -E '^OPENROUTER_API_KEY=' "$OR_ENV" 2>/dev/null | sed 's/^OPENROUTER_API_KEY=//')
  if [ -z "$key" ]; then
    echo "Error: OPENROUTER_API_KEY not found in $OR_ENV" >&2
    return 1
  fi
  shift 2>/dev/null || true
  ANTHROPIC_API_KEY="$key" \
  ANTHROPIC_BASE_URL="http://127.0.0.1:$OR_PROXY_PORT" \
  claude "$@"
}

# Convenience variants
claude-or-sonnet() { claude-or "claude-sonnet-5" "$@"; }
claude-or-opus()   { claude-or "claude-opus-4-8" "$@"; }
claude-or-haiku()  { claude-or "claude-haiku-4-5" "$@"; }

# Kill the proxy
claude-or-stop() {
  local pid
  pid=$(lsof -ti :$OR_PROXY_PORT 2>/dev/null)
  if [ -n "$pid" ]; then kill "$pid" 2>/dev/null; echo "OR proxy stopped"; fi
}

# ── Claude Code via Local Models (free-claude-code proxy) ──────────
FCC_ORNITH_PORT="${FCC_ORNITH_PORT:-8097}"
FCC_QWEN_PORT="${FCC_QWEN_PORT:-8098}"
ORNITH_MODEL="$HOME/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf"
QWEN_MODEL="$HOME/models/qwen3.6-27b-mtp-Q3_K_S.gguf"

# ── ccornith — Claude Code with Ornith-1.0-9B Q5 (local) ──────────
# Benchmarks (RTX 5080, vanilla build): pp512=6044 t/s, tg128=131 t/s
# Best: vanilla build, -t 6, flash-attn on
ccornith() {
  _ensure_ornith_server
  _ensure_ornith_fcc_proxy
  PORT=$FCC_ORNITH_PORT fcc-claude --model "ornith-1.0-9b-Q5_K_M.gguf" "$@"
}

# ── ccqwen — Claude Code with Qwen3.6-27B MTP (local) ─────────────
# Benchmarks (RTX 5080, vanilla build): pp512=1692 t/s, tg128=47 t/s (+MTP ≈96)
# Best: vanilla build, -t 8, MTP on, flash-attn on
ccqwen() {
  _ensure_qwen_server
  _ensure_qwen_fcc_proxy
  PORT=$FCC_QWEN_PORT fcc-claude --model "qwen3.6-27b-mtp-Q3_K_S.gguf" "$@"
}

# Legacy alias
claude-local() { ccornith "$@"; }

ccstop() {
  local pid
  pid=$(lsof -ti :$FCC_ORNITH_PORT 2>/dev/null)
  [ -n "$pid" ] && kill "$pid" 2>/dev/null && echo "Ornith FCC proxy stopped"
  pid=$(lsof -ti :$FCC_QWEN_PORT 2>/dev/null)
  [ -n "$pid" ] && kill "$pid" 2>/dev/null && echo "Qwen FCC proxy stopped"
}

# ── Server helpers ─────────────────────────────────────────────────

_ensure_ornith_server() {
  if lsof -i :8082 >/dev/null 2>&1; then
    curl -s http://127.0.0.1:8082/v1/models >/dev/null 2>&1 && return 0
    echo "Ornith server running but not ready — waiting..." >&2
    for i in $(seq 1 15); do
      curl -s http://127.0.0.1:8082/v1/models >/dev/null 2>&1 && return 0
      sleep 2
    done
    return 1
  fi
  # Only one model fits in VRAM — kill Qwen if running
  if lsof -i :8080 >/dev/null 2>&1; then
    echo "Stopping Qwen server to free VRAM..." >&2
    kill $(lsof -ti :8080) 2>/dev/null
    sleep 2
  fi
  echo "Starting Ornith Q5 server on :8082..."
  export LD_LIBRARY_PATH="$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH"
  nohup "$HOME/llama.cpp/build/bin/llama-server" \
    -m "$ORNITH_MODEL" \
    -ngl 99 -t 6 -c 200000 --port 8082 --host 127.0.0.1 \
    --temp 0.6 --top-p 0.95 --top-k 20 \
    -ub 4096 -b 4096 --cache-reuse 256 \
    --flash-attn on --reasoning-preserve \
    --cache-type-k q8_0 --cache-type-v q8_0 \
    -np 6 --kv-unified \
    > /tmp/ornith-server.log 2>&1 & disown
  for i in $(seq 1 25); do
    if curl -s http://127.0.0.1:8082/v1/models >/dev/null 2>&1; then
      echo "Ornith server ready (${i}s)"; return 0
    fi
    sleep 2
  done
  echo "Ornith server failed to start within 50s" >&2
  return 1
}

_ensure_qwen_server() {
  if lsof -i :8080 >/dev/null 2>&1; then
    curl -s http://127.0.0.1:8080/v1/models >/dev/null 2>&1 && return 0
    echo "Qwen server running but not ready — waiting..." >&2
    for i in $(seq 1 30); do
      curl -s http://127.0.0.1:8080/v1/models >/dev/null 2>&1 && return 0
      sleep 2
    done
    echo "Qwen server still not ready after 60s" >&2
    return 1
  fi
  # Only one model fits in VRAM — kill Ornith if running
  if lsof -i :8082 >/dev/null 2>&1; then
    echo "Stopping Ornith server to free VRAM..." >&2
    kill $(lsof -ti :8082) 2>/dev/null
    sleep 2
  fi
  echo "Starting Qwen3.6-27B MTP server on :8080..."
  export LD_LIBRARY_PATH="$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH"
  nohup "$HOME/llama.cpp/build/bin/llama-server" \
    -m "$QWEN_MODEL" \
    -ngl 99 -t 8 -c 200000 --port 8080 --host 127.0.0.1 \
    --no-kv-offload \
    --temp 0.7 --top-p 0.95 --top-k 40 \
    --spec-type draft-mtp --spec-draft-n-max 2 \
    --flash-attn on \
    --cache-type-k q4_0 --cache-type-v q4_0 \
    -np 2 --cache-reuse 256 \
    > /tmp/qwen-server.log 2>&1 & disown
  for i in $(seq 1 45); do
    if curl -s http://127.0.0.1:8080/v1/models >/dev/null 2>&1; then
      echo "Qwen server ready (${i}s)"; return 0
    fi
    sleep 2
  done
  echo "Qwen server failed to start within 90s — check /tmp/qwen-server.log" >&2
  return 1
}

# ── FCC proxy helpers ───────────────────────────────────────────────

_ensure_ornith_fcc_proxy() {
  if lsof -i :$FCC_ORNITH_PORT >/dev/null 2>&1; then return 0; fi
  echo "Starting FCC proxy for Ornith on :$FCC_ORNITH_PORT..."
  PORT=$FCC_ORNITH_PORT LLAMACPP_BASE_URL="http://127.0.0.1:8082/v1" \
    MODEL="llamacpp/ornith-1.0-9b-Q5_K_M.gguf" \
    ENABLE_WEB_SERVER_TOOLS=true FCC_AUTO_INTERCEPT_WEB_TOOLS=true \
    nohup fcc-server > /tmp/fcc-ornith.log 2>&1 & disown
  for i in $(seq 1 10); do
    if curl -s http://127.0.0.1:$FCC_ORNITH_PORT/health >/dev/null 2>&1; then
      echo "FCC Ornith proxy ready (${i}s)"; break
    fi
    sleep 1
  done
}

_ensure_qwen_fcc_proxy() {
  if lsof -i :$FCC_QWEN_PORT >/dev/null 2>&1; then return 0; fi
  echo "Starting FCC proxy for Qwen on :$FCC_QWEN_PORT..."
  PORT=$FCC_QWEN_PORT LLAMACPP_BASE_URL="http://127.0.0.1:8080/v1" \
    MODEL="llamacpp/qwen3.6-27b-mtp-Q3_K_S.gguf" \
    ENABLE_WEB_SERVER_TOOLS=true FCC_AUTO_INTERCEPT_WEB_TOOLS=true \
    nohup fcc-server > /tmp/fcc-qwen.log 2>&1 & disown
  for i in $(seq 1 10); do
    if curl -s http://127.0.0.1:$FCC_QWEN_PORT/health >/dev/null 2>&1; then
      echo "FCC Qwen proxy ready (${i}s)"; break
    fi
    sleep 1
  done
}

# ── OpenCode via OpenRouter ───────────────────────────────────────
code() {
  export OPENCODE_ENABLE_EXA=1
  local model="$1"
  case "$model" in
    deepseek-v4-pro|ds-pro|dsp)  model="openrouter/deepseek/deepseek-v4-pro" ;;
    deepseek-v4-flash|ds-flash|dsf|ds) model="openrouter/deepseek/deepseek-v4-flash" ;;
    glm|glm5)                     model="openrouter/z-ai/glm-5.2" ;;
    qwen|qwen3.6)                 model="openrouter/qwen/qwen3.6-27b" ;;
    qwen-flash|qwf)              model="openrouter/qwen/qwen3.6-flash" ;;
    qwen-coder|qwc)              model="openrouter/qwen/qwen3-coder-plus" ;;
    ornith)
      _ensure_ornith_server
      model="ornith/ornith-1.0-9b-Q5_K_M.gguf" ;;
    local)
      _ensure_qwen_server
      model="local/qwen3.6-27b-mtp-Q3_K_S.gguf" ;;
    status|models)                exec "$HOME/Development/local-llms/scripts/model-status.sh" ;;
    "")                           opencode; return ;;
    *)                            model="openrouter/$model" ;;
  esac
  shift 2>/dev/null || true
  opencode -m "$model" "$@"
}

# Completions for the `code` function (only in interactive zsh)
if command -v compdef >/dev/null 2>&1; then
  _code_model() {
    local -a models
    models=(
      "deepseek-v4-pro:DeepSeek V4 Pro via OpenRouter"
      "ds-pro:DeepSeek V4 Pro"
      "dsp:DeepSeek V4 Pro"
      "deepseek-v4-flash:DeepSeek V4 Flash via OpenRouter"
      "ds-flash:DeepSeek V4 Flash"
      "dsf:DeepSeek V4 Flash"
      "ds:DeepSeek V4 Flash"
      "glm:GLM 5.2 via OpenRouter"
      "glm5:GLM 5.2"
      "qwen:Qwen 3.6 27B via OpenRouter"
      "qwen3.6:Qwen 3.6 27B"
      "qwen-flash:Qwen 3.6 Flash"
      "qwf:Qwen 3.6 Flash"
      "qwen-coder:Qwen 3 Coder Plus"
      "qwc:Qwen 3 Coder Plus"
      "ornith:Ornith-1.0-9B Q5_K_M (local)"
      "local:Qwen3.6-27B MTP (local llama.cpp)"
      "status:Show running servers and configured models"
      "models:Show running servers and configured models"
    )
    _describe 'model' models
  }
  compdef _code_model code
fi

# ── yt-transcript shortcut ────────────────────────────────────────
alias yt-transcript="$HOME/Development/local-llms/yt-transcript"
