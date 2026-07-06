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

# ── Claude Code via Local Ornith (free-claude-code proxy) ──────────
FCC_PORT="${FCC_PORT:-8097}"
ORNITH_MODEL="$HOME/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf"

claude-local() {
  _ensure_ornith_server
  _ensure_fcc_proxy
  PORT=$FCC_PORT fcc-claude "$@"
}

claude-local-stop() {
  local pid
  pid=$(lsof -ti :$FCC_PORT 2>/dev/null)
  if [ -n "$pid" ]; then kill "$pid" 2>/dev/null; echo "FCC proxy stopped"; else echo "No proxy running"; fi
}

_ensure_ornith_server() {
  if lsof -i :8082 >/dev/null 2>&1; then return 0; fi
  echo "Starting Ornith Q5 server on :8082..."
  export LD_LIBRARY_PATH="$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH"
  nohup "$HOME/llama.cpp/build/bin/llama-server" \
    -m "$ORNITH_MODEL" \
    -ngl 99 -t 8 -c 200000 --port 8082 --host 127.0.0.1 \
    --temp 0.6 --top-p 0.95 --top-k 20 \
    -ub 4096 -b 4096 --cache-reuse 256 \
    --flash-attn on --reasoning-preserve \
    --cache-type-k q8_0 --cache-type-v q8_0 \
    -np 6 --kv-unified \
    > /tmp/ornith-server.log 2>&1 & disown
  for i in $(seq 1 30); do
    if curl -s http://127.0.0.1:8082/health >/dev/null 2>&1; then
      echo "Ornith server ready (${i}s)"; break
    fi
    sleep 1
  done
}

_ensure_fcc_proxy() {
  if lsof -i :$FCC_PORT >/dev/null 2>&1; then return 0; fi
  echo "Starting free-claude-code proxy on :$FCC_PORT..."
  PORT=$FCC_PORT LLAMACPP_BASE_URL="http://127.0.0.1:8082/v1" \
    MODEL="llamacpp/ornith-1.0-9b-Q5_K_M.gguf" \
    ENABLE_WEB_SERVER_TOOLS=true FCC_AUTO_INTERCEPT_WEB_TOOLS=true \
    nohup fcc-server > /tmp/fcc-server.log 2>&1 & disown
  for i in $(seq 1 10); do
    if curl -s http://127.0.0.1:$FCC_PORT/health >/dev/null 2>&1; then
      echo "FCC proxy ready (${i}s)"; break
    fi
    sleep 1
  done
}

# Completions for claude-local (model names for local Ornith)
if command -v compdef >/dev/null 2>&1; then
  _claude_local() {
    local -a models
    models=(
      "claude-opus-4-8:Opus 4.8 (via OpenRouter)"
      "claude-sonnet-5:Sonnet 5 (via OpenRouter)"
      "claude-haiku-4-5:Haiku 4.5 (via OpenRouter)"
    )
    _describe 'model' models
  }
  compdef _claude_local claude-local
fi

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
      # Auto-start Qwen server if not running
      if ! lsof -i :8080 >/dev/null 2>&1; then
        echo "Starting Qwen3.6-27B MTP server on :8080..."
        export LD_LIBRARY_PATH="$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH"
        nohup "$HOME/llama.cpp/build/bin/llama-server" \
          -m "$HOME/models/qwen3.6-27b-mtp-Q3_K_S.gguf" \
          -ngl 99 --port 8080 \
          --spec-type draft-mtp --spec-draft-n-max 2 \
          > /tmp/qwen-server.log 2>&1 & disown
        for i in $(seq 1 45); do
          if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
            echo "Qwen server ready (${i}s)"
            break
          fi
          sleep 1
        done
      fi
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
