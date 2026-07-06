#!/usr/bin/env bash
# Query running local model servers and show available models.
# Used by `code status` and opencode model discovery.

set -euo pipefail

SERVERS=(
  "8080:Qwen3.6-27B MTP"
  "8082:Ornith-1.0-9B"
)

any_running=false

for entry in "${SERVERS[@]}"; do
  port="${entry%%:*}"
  label="${entry#*:}"

  if curl -sf "http://127.0.0.1:$port/v1/models" >/dev/null 2>&1; then
    if ! $any_running; then
      echo "RUNNING MODELS"
      echo "─────────────"
      any_running=true
    fi
    model=$(curl -sf "http://127.0.0.1:$port/v1/models" 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    models = data.get('data', [])
    for m in models:
        print(m.get('id', 'unknown'))
except: pass
" 2>/dev/null | head -1)
    echo "  :$port  $label  ←  $(basename "${model:-unknown}")"
  fi
done

if ! $any_running; then
  echo "No local model servers running."
  echo "Start one with:"
  echo "  claude-local    # starts Ornith on :8082"
  echo "  llama-server    # see CLAUDE.md for commands"
fi

echo
echo "CONFIGURED MODELS (from opencode.json)"
echo "─────────────────────────────────────"
python3 -c "
import json, os
path = os.path.expanduser('~/Development/local-llms/opencode.json')
with open(path) as f:
    cfg = json.load(f)
for prov, pcfg in cfg.get('provider', {}).items():
    if pcfg.get('api') != 'openai':
        continue
    base = pcfg.get('options', {}).get('baseURL', '')
    models = pcfg.get('models', {})
    if not models:
        continue
    print(f'  {prov}  ({base})')
    for mid, mcfg in models.items():
        print(f'    {mid}  —  {mcfg.get(\"name\", mid)}')
" 2>/dev/null || echo "  (could not read opencode.json)"
