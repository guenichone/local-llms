# OmniRoute: Run in Parallel With Existing Stack

## Context

We have a working, battle-tested stack (~540 lines of `patches/providers.zsh`) managing 3 proxy layers, 7+ ports, VRAM arbitration, and model selection. OmniRoute is a free MIT AI gateway (21K+ stars) that provides: one endpoint, 271+ providers (90+ free), 18 routing strategies, token compression (RTK + Caveman, 15-95% savings), and a 4-tier auto-fallback cascade.

**Goal:** Run OmniRoute **alongside** the existing stack — zero deletions, zero regressions. OmniRoute becomes a new front door that can route to free tiers + our existing OpenCode Go subscription + local models as backends.

**Constraints:**
- Docker install preferred (isolated, no Node.js dependency pollution)
- Paid tier via `OPENCODE_GO_API_KEY` (DeepSeek V4 Flash/Pro, $10/mo) — no OpenRouter

---

## The Key Insight: Our Proxies Become OmniRoute Backends

OmniRoute connects to any OpenAI-compatible endpoint. Our existing proxies and servers expose these protocols:

| Existing Service | Port | Protocol | Can OmniRoute use it as backend? |
|---|---|---|---|
| llama-server (Ornith) | 8082 | OpenAI `/v1` | ✅ Direct — no proxy needed |
| llama-server (Qwen) | 8080 | OpenAI `/v1` | ✅ Direct — no proxy needed |
| llama-server (Qwopus) | 8083 | OpenAI `/v1` | ✅ Direct — no proxy needed |
| llama-server (Gemma 4) | 8084 | OpenAI `/v1` | ✅ Direct — no proxy needed |
| `opencode-claude-proxy` | 8787 | Anthropic front → OpenAI back | ✅ OmniRoute can route to OpenCode's API directly (bypass proxy) OR use proxy as Anthropic backend |

**For local models:** OmniRoute talks directly to llama-server's `/v1` — bypassing the FCC proxies. The FCC proxies stay in place for the direct `ccornith`/`ccqwen`/`ccqwopus` aliases.

**For OpenCode Go:** OmniRoute connects to OpenCode's API directly as an OpenAI-compatible backend using `OPENCODE_GO_API_KEY`. The `opencode-claude-proxy` on :8787 stays for `claude-go`.

---

## Parallel Architecture

```
                          ┌── NEW PATH ──────────────────────────────────────┐
                          │                                                    │
                          │  Claude Code ──→ OmniRoute (:20128) ──→ [         │
                          │    claude-omni      auto/coding          Free tiers│
                          │    code-omni                             OpenCode G│
                          │    hermes-omni                           llama.cpp │
                          │                                           :8080   │
                          │                                           :8082   │
                          │                                           :8083   │
                          │                                         ]          │
                          │                                                    │
┌─────────────────────────┼── EXISTING PATHS (unchanged) ─────────────────────┤
│                         │                                                    │
│  Claude Code ──→ fcc-server (:8097) ──→ llama :8082        ccornith         │
│  Claude Code ──→ fcc-server (:8098) ──→ llama :8080        ccqwen           │
│  Claude Code ──→ fcc-server (:8100) ──→ llama :8083        ccqwopus         │
��  Claude Code ──→ go-proxy (:8787) ──→ OpenCode Go          claude-go        │
│  Claude Code ──→ or-proxy (:8099) ──→ OpenRouter            claude-or        │
│                                                                              │
│  OpenCode ──→ direct OpenRouter / llama.cpp                code ds/ornith   │
│  Hermes ──→ direct llama.cpp / DeepSeek API                hermes-ornith    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Key property:** Every existing alias continues to work exactly as before. The new OmniRoute aliases are **additions**, not replacements.

---

## Port Map (No Conflicts)

| Port | Service | Stack |
|---|---|---|
| 20128 | OmniRoute API (Docker) | NEW |
| 20129 | OmniRoute Dashboard (web UI) | NEW |
| 8080 | Qwen llama-server | existing |
| 8082 | Ornith llama-server | existing |
| 8083 | Qwopus llama-server | existing |
| 8084 | Gemma 4 llama-server | existing |
| 8097 | FCC Ornith proxy | existing |
| 8098 | FCC Qwen proxy | existing |
| 8099 | OR proxy | existing |
| 8100 | FCC Qwopus proxy | existing |
| 8787 | Go proxy | existing |

---

## Docker Installation

### One-time setup

```bash
# Pull and start OmniRoute (API :20128, Dashboard :20129)
docker run -d \
  --name omniroute \
  --restart unless-stopped \
  -p 127.0.0.1:20128:20128 \
  -p 127.0.0.1:20129:20129 \
  -v omniroute-data:/app/data \
  diegosouzapw/omniroute:latest

# Check it's running
curl -s http://localhost:20128/health
```

### Lifecycle

```bash
docker start omniroute   # start (if stopped)
docker stop omniroute    # stop
docker logs omniroute    # view logs
docker rm -f omniroute   # remove entirely
```

### Optional: auto-start via our shell helpers

```bash
# Add to providers.zsh — tiny helper
_ensure_omniroute() {
  if curl -s http://localhost:20128/health >/dev/null 2>&1; then
    return 0
  fi
  echo "Starting OmniRoute..." >&2
  docker start omniroute >/dev/null 2>&1 || \
    docker run -d --name omniroute --restart unless-stopped \
      -p 127.0.0.1:20128:20128 -p 127.0.0.1:20129:20129 \
      -v omniroute-data:/app/data \
      diegosouzapw/omniroute:latest
  sleep 3
}

# Also add to cctop: docker stop omniroute
```

---

## OmniRoute Configuration (Web Dashboard at :20129)

### Tier 1: Free Providers (~$0)
OmniRoute auto-discovers 90+ free tiers. Just leave them enabled — they handle simple tasks at zero cost.

### Tier 2: OpenCode Go ($10/mo flat — our paid tier)
Configure as a custom OpenAI-compatible provider in OmniRoute:
- **Base URL:** OpenCode Go's API endpoint (TBD — discover from `opencode-claude-proxy` config or OpenCode docs)
- **API Key:** `$OPENCODE_GO_API_KEY` from our `.env`
- **Models:** `deepseek-v4-flash` (default), `deepseek-v4-pro`

### Tier 3: Local llama.cpp servers (free, already running)
Add as custom OpenAI providers:
- `http://127.0.0.1:8082/v1` — Ornith-1.0-9B Q5_K_M
- `http://127.0.0.1:8080/v1` — Qwen3.6-27B MTP
- `http://127.0.0.1:8083/v1` — Qwopus 35B Nano
- `http://127.0.0.1:8084/v1` — Gemma 4 E4B

### Default Combo: `auto/coding`
```
Free tiers → OpenCode Go (DeepSeek Flash) → Local models (last resort)
```
Rationale: burn free quota first, escalate to our $10/mo sub when needed, fall back to local only when offline or budget exhausted.

---

## New Aliases to Add

```bash
# ── Claude Code via OmniRoute ──

claude-omni() {
  local model="${1:-auto/coding}"
  shift 2>/dev/null || true
  _ensure_omniroute
  ANTHROPIC_BASE_URL="http://localhost:20128/v1" \
  ANTHROPIC_API_KEY="sk-omniroute-local" \
  claude --model "$model" "$@"
}

# Convenience variants
claude-omni-free()   { claude-omni "auto/cheap" "$@"; }    # maximize free tiers
claude-omni-fast()   { claude-omni "auto/fast" "$@"; }     # lowest latency first
claude-omni-local()  { claude-omni "auto/local-first" "$@"; } # local first, then escalate

# ── OpenCode via OmniRoute ──
code-omni() {
  local model="${1:-auto}"
  shift 2>/dev/null || true
  opencode -m "omniroute/$model" "$@"
}
```

---

## Day-to-Day Usage

```bash
# ── Existing paths (unchanged) ──
ccornith              # Ornith Q5 local — offline, free, ~30s TTFT
ccqwopus              # Qwopus 35B Nano local — best quality local
claude-go             # DeepSeek via OpenCode Go — $10/mo flat, predictable
claude-or             # Opus 4.8 via OpenRouter — pay-per-token, best quality

# ── New OmniRoute paths ──
claude-omni           # auto/coding — free tiers first, then OpenCode Go, then local
claude-omni auto/fast # lowest latency (likely hits local first)
claude-omni-free      # maximize free usage, minimize spend
claude-omni-local     # local-first then escalate
```

---

## What OmniRoute Adds (Without Removing Anything)

| Capability | Before OmniRoute | After (with OmniRoute in parallel) |
|---|---|---|
| Free tier access | None — we pay for everything | ~1.4B free tokens/mo via auto combo |
| Auto-fallback | Manual alias switching | Automatic 4-tier cascade within same session |
| Token compression | Reactive hook warns at 85% context | Preventive RTK + Caveman compression (15-95% savings) |
| Provider dashboard | `cat .env | grep KEY` + OpenRouter billing page | Live web UI at :20129 |
| Model selection | 10+ aliases to remember | `claude-omni` with `auto` covers most cases |
| Cost optimization | Manual: "use local when possible" | `auto/cheap` maximizes free, only spends when needed |
| MCP tools | Claude Code's built-in | +104 OmniRoute MCP tools (optional) |

---

## Adoption Path (Incremental, Reversible)

### Phase 1: Install & Explore (30 min)
1. `docker pull diegosouzapw/omniroute:latest`
2. `docker run -d --name omniroute --restart unless-stopped -p 127.0.0.1:20128:20128 -p 127.0.0.1:20129:20129 -v omniroute-data:/app/data diegosouzapw/omniroute:latest`
3. Open `http://localhost:20129` — browse dashboard, free tiers catalog
4. Add `claude-omni` alias to `providers.zsh`

### Phase 2: Test Free Tiers Only (15 min)
1. No keys connected — just free tiers
2. `claude-omni auto/cheap -p "write hello world in python" --print`
3. See if free tier quality is acceptable for simple tasks

### Phase 3: Connect OpenCode Go (30 min)
1. Find OpenCode Go's OpenAI-compatible base URL (check `opencode-claude-proxy` config for upstream URL)
2. Add as custom OpenAI provider in OmniRoute dashboard
3. Create `auto/coding` combo: free tiers → OpenCode Go
4. Test: `claude-omni -p "write a fibonacci function in rust" --print`

### Phase 4: Add Local Models as Backends (30 min)
1. Add `http://127.0.0.1:8082/v1`, `:8080`, `:8083` as custom OpenAI providers
2. Create `auto/local-first` combo: local → OpenCode Go → free tiers
3. Test: `claude-omni auto/local-first -p "fibonacci"` — should hit Ornith
4. Kill Ornith server — verify auto-fallback to OpenCode Go

### Phase 5: Daily Use (weeks)
1. Use `claude-omni` as default; keep `ccornith`/`claude-go`/`claude-or` for explicit control
2. Monitor dashboard for free tier savings
3. Tune combos based on observed quality/latency

### What We NEVER Delete
- `or-proxy.mjs` — still used by `claude-or`
- All FCC proxy configs — still used by `ccornith`/`ccqwen`/`ccqwopus`
- `opencode-claude-proxy` — still used by `claude-go`
- All existing shell aliases — they keep working
- `check-context.sh` hook — still protects local model sessions

---

## Verification Plan

1. **Docker start** — `docker run -d --name omniroute --restart unless-stopped -p 127.0.0.1:20128:20128 -p 127.0.0.1:20129:20129 -v omniroute-data:/app/data diegosouzapw/omniroute:latest`
2. **Health check** — `curl -s http://localhost:20128/health`
3. **Dashboard** — open `http://localhost:20129`, verify free tier catalog loads
4. **Zero port conflicts** — `lsof -i :20128` (OmniRoute) alongside `lsof -i :8787` (Go proxy), `lsof -i :8082` (Ornith) — all running
5. **Test free tier** — `claude-omni auto/cheap -p "what is 2+2?" --print`
6. **Test OpenCode Go** — add key in dashboard, `claude-omni -p "write fibonacci" --print`
7. **Test local backend** — add `:8082/v1`, `claude-omni auto/local-first` → verify Ornith responds
8. **Test fallback** — kill Ornith, same command → OmniRoute escalates to OpenCode Go
9. **Existing aliases unchanged** — `ccornith`, `ccqwen`, `claude-go`, `claude-or` all work
10. **Benchmark** — `bench ornith-1.0-9b Q5_K_M` — models perform identically
