#!/bin/bash
# Gate: only activate for local-model sessions
if [ -z "$CLAUDE_LOCAL_MODEL" ]; then
  exit 0
fi

THRESHOLD=85  # warn at 85%+ usage
PORT="${CLAUDE_LOCAL_MODEL_PORT:-8082}"

data=$(curl -s --max-time 2 "http://127.0.0.1:${PORT}/slots" 2>/dev/null)
if [ -z "$data" ]; then
  exit 0
fi

usage=$(echo "$data" | python3 -c "
import json,sys
try:
    slots = json.load(sys.stdin)
except:
    sys.exit(0)
for s in slots:
    tok = s.get('n_prompt_tokens', 0) or 0
    ctx = s.get('n_ctx', 0) or 1
    pct = int(tok / ctx * 100)
    if pct >= $THRESHOLD:
        print(f'{pct}:{tok}/{ctx}')
        break
" 2>/dev/null)

if [ -n "$usage" ]; then
  pct="${usage%%:*}"
  rest="${usage#*:}"
  echo "{\"systemMessage\":\"Context at ${pct}% (${rest}) on port ${PORT}. Run /compact now to prevent overflow.\",\"hookSpecificOutput\":{\"hookEventName\":\"PostToolBatch\"}}"
fi
exit 0
