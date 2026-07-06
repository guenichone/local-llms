#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${1:-$HOME/models/ornith-1.0-9b/ornith-1.0-9b-Q4_K_M.gguf}"
MODEL_NAME="$(basename "$MODEL_PATH")"
PORT=8082
LLAMA_SERVER="$HOME/llama.cpp/build/bin/llama-server"
LLAMA_CLI="$HOME/llama.cpp/build/bin/llama-cli"

echo "=== Benchmark: $MODEL_NAME ==="
echo ""

# ── CLI benchmark (single turn, no server) ──────────────────────
bench_cli() {
  local prompt="$1" n="$2"
  echo "--- CLI: prompt processing ---"
  $LLAMA_CLI -m "$MODEL_PATH" -ngl 99 -t 8 -n 1 \
    --single-turn --no-display-prompt \
    --prompt "$prompt" 2>&1 | grep -oP 'Prompt: [\d.]+ t/s' || echo "N/A"

  echo "--- CLI: generation ($n tokens) ---"
  $LLAMA_CLI -m "$MODEL_PATH" -ngl 99 -t 8 -n "$n" \
    --single-turn --no-display-prompt \
    --prompt "$prompt" 2>&1 | grep -oP 'Generation: [\d.]+ t/s' || echo "N/A"
}

bench_api() {
  echo "--- API server ---"
  $LLAMA_SERVER -m "$MODEL_PATH" -ngl 99 -t 8 -c 32768 \
    --port $PORT --host 127.0.0.1 &>/tmp/llama-bench-$$.log &
  local pid=$!
  sleep 4

  # Prompt processing (short prompt)
  curl -s -X POST "http://127.0.0.1:$PORT/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"hello"}],"temperature":0.6,"max_tokens":1}' \
    2>&1 | python3 -c "
import json,sys
d=json.load(sys.stdin)
t=d['timings']
print(f\"  Prompt: {t['prompt_per_second']:.1f} t/s\")
print(f\"  Gen:    {t['predicted_per_second']:.1f} t/s\")
print(f\"  Cache:  {t['cache_n']} tokens\")
"

  # Generation benchmark (long prompt + many tokens)
  curl -s -X POST "http://127.0.0.1:$PORT/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{"messages":[{"role":"user","content":"write a detailed explanation of how transformers work in machine learning, include attention mechanisms, feed-forward networks, and the overall architecture. be thorough and cover at least 5 paragraphs."}],"temperature":0.6,"max_tokens":512}' \
    2>&1 | python3 -c "
import json,sys
d=json.load(sys.stdin)
t=d['timings']
u=d['usage']
print(f\"  Prompt: {t['prompt_per_second']:.1f} t/s ({u['prompt_tokens']} tokens)\")
print(f\"  Gen:    {t['predicted_per_second']:.1f} t/s ({u['completion_tokens']} tokens)\")
print(f\"  Total:  {u['total_tokens']} tokens in {(t['prompt_ms']+t['predicted_ms'])/1000:.1f}s\")
"

  kill "$pid" 2>/dev/null
  wait "$pid" 2>/dev/null || true
}

bench_cli "Write a brief explanation of attention mechanisms in transformers." 256
echo ""
bench_api
echo ""
echo "=== Done ==="
