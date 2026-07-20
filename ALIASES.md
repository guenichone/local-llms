# Aliases, Hooks & Prompts

Single reference for every alias, hook, prompt, and server defined in this repo.
For model benchmarks and setup details, see [CLAUDE.md](./CLAUDE.md).
For external references (papers, videos, repos), see [REFERENCES.md](./REFERENCES.md).

---

## Quick Reference

```bash
# Claude Code
claude-or                   # Opus 4.8 via OpenRouter ($)
claude-or-sonnet            # Sonnet 5 via OpenRouter
ccornith                    # Ornith Q5 (local, free)
ccqwen                      # Qwen3.6-27B MTP (local)
ccqwopus                    # Qwopus 35B Nano (local)
ccstop                      # Kill all servers + proxies

# OpenCode
code                        # TUI model picker
code ornith                 # Ornith Q5 (local)
code local                  # Qwen3.6-27B MTP (local)
code qwopus                 # Qwopus 35B Nano (local)
code ds                     # DeepSeek V4 Flash (OpenRouter)
code dsp                    # DeepSeek V4 Pro (OpenRouter)
code glm                    # GLM 5.2 (OpenRouter)

# Hermes Agent
hermes-ornith               # Ornith Q5 (local)
hermes-qwopus               # Qwopus 35B Nano (local)
hermes-gemma                # Gemma 4 E4B (local)
hermes-ds                   # DeepSeek V4 Pro (remote)

# Utilities
yt-transcript <url>         # YouTube transcript + metadata
```

---

## Server Port Map

| Port | Model | Size | Context | Build | Alias triggers |
|---|---|---|---|---|---|
| 8080 | Qwen3.6-27B MTP Q3_K_S | 12 GB | 200K | turboquant, turbo3 KV | `ccqwen`, `code local` |
| 8082 | Ornith-1.0-9B Q5_K_M | 6 GB | 200K | vanilla llama.cpp | `ccornith`, `code ornith`, `hermes-ornith` |
| 8083 | Qwopus 35B Nano (MTP) | 11 GB | 131K | turboquant | `ccqwopus`, `code qwopus`, `hermes-qwopus` |
| 8084 | Gemma 4 E4B Q4_K_M | 3 GB | 32K | vanilla llama.cpp | `hermes-gemma` |

FCC proxy ports: 8097 (Ornith), 8098 (Qwen), 8100 (Qwopus).
OpenRouter proxy port: 8099.

Only one large model fits in 16 GB VRAM at a time. Aliases auto-kill conflicting servers.
Gemma 4 E4B (3 GB) is the exception — it coexists alongside any other model.

---

## Claude Code Aliases

Defined in [`patches/providers.zsh`](./patches/providers.zsh), sourced from `~/.zshrc.d/providers.zsh`.

### Cloud (OpenRouter)

| Alias | Model | Resolves to |
|---|---|---|
| `claude-or` | Claude Opus 4.8 (default) | `anthropic/claude-opus-4-8` |
| `claude-or-sonnet` | Claude Sonnet 5 | `anthropic/claude-sonnet-5` |
| `claude-or-haiku` | Claude Haiku 4.5 | `anthropic/claude-haiku-4.5` |
| `claude-or-stop` | — | kills the OR proxy |

Requires `OPENROUTER_API_KEY` in `.env`. Uses a Node proxy (`or-proxy.mjs`) on `:8099` to translate model names.

### Local (llama.cpp via FCC proxy)

| Alias | Model | Port | Env vars set |
|---|---|---|---|
| `ccornith` | Ornith-1.0-9B Q5_K_M | :8082 | `CLAUDE_LOCAL_MODEL=1` `CLAUDE_LOCAL_MODEL_PORT=8082` |
| `ccqwen` | Qwen3.6-27B MTP Q3_K_S | :8080 | `CLAUDE_LOCAL_MODEL=1` `CLAUDE_LOCAL_MODEL_PORT=8080` |
| `ccqwopus` | Qwopus 35B Nano MTP | :8083 | `CLAUDE_LOCAL_MODEL=1` `CLAUDE_LOCAL_MODEL_PORT=8083` |
| `ccstop` | — | — | kills all FCC proxies + llama-servers |

Each alias:
1. Auto-starts the llama-server if not running (kills conflicting models to free VRAM)
2. Auto-starts the FCC proxy on its dedicated port
3. Appends `agents/claude-code/prompts/local-agent.md (copy to ~/.claude/contexts/)` as system prompt
4. Sets `CLAUDE_LOCAL_MODEL` env vars for the context-check hook

---

## OpenCode Aliases

Defined in [`patches/providers.zsh`](./patches/providers.zsh), `code()` function.

### Local models

| Shortcut | Resolves to |
|---|---|
| `code ornith` | `ornith/ornith-1.0-9b-Q5_K_M.gguf` |
| `code local` | `local/qwen3.6-27b-mtp-Q3_K_S.gguf` |
| `code qwopus` | (not yet in opencode.json — uses direct URL) |

Local model aliases auto-start the llama-server before launching OpenCode.

### Cloud models (OpenRouter)

| Shortcut | Resolves to |
|---|---|
| `code ds` / `dsf` / `ds-flash` | `openrouter/deepseek/deepseek-v4-flash` |
| `code dsp` / `ds-pro` | `openrouter/deepseek/deepseek-v4-pro` |
| `code glm` / `glm5` | `openrouter/z-ai/glm-5.2` |
| `code qwen` / `qwen3.6` | `openrouter/qwen/qwen3.6-27b` |
| `code qwf` / `qwen-flash` | `openrouter/qwen/qwen3.6-flash` |
| `code qwc` / `qwen-coder` | `openrouter/qwen/qwen3-coder-plus` |
| `code status` / `models` | runs `scripts/model-status.sh` |
| `code <anything>` | `openrouter/<anything>` |

Provider config in [`opencode.json`](./opencode.json).

---

## Hermes Agent Aliases

Defined in [`patches/providers.zsh`](./patches/providers.zsh). Each alias invokes a Hermes profile wrapper.

| Alias | Profile | Model | Provider | Port |
|---|---|---|---|---|
| `hermes-ornith` | `ornith` | Ornith Q5_K_M | custom (llama.cpp) | :8082 |
| `hermes-qwopus` | `qwopus` | Qwopus 35B Nano | custom (llama.cpp) | :8083 |
| `hermes-gemma` | `gemma4` | Gemma 4 E4B | custom (llama.cpp) | :8084 |
| `hermes-ds` | `deepseek-v4-pro` | DeepSeek V4 Pro | deepseek (built-in) | remote |

Profiles live in `~/.hermes/profiles/<name>/`. Wrappers in `~/.local/bin/{ornith,qwopus,gemma4,deepseek}`.

### Hermes Profile Configs (reference)

```
~/.hermes/profiles/
  ornith/          provider: custom,  base_url: :8082,  ctx: 200K,   max_tok: 8192
  qwopus/          provider: custom,  base_url: :8083,  ctx: 131K,   max_tok: 8192
  gemma4/          provider: custom,  base_url: :8084,  ctx: 32K,    max_tok: 4096
  deepseek-v4-pro/ provider: deepseek                     ctx: 1M,     max_tok: 65536
```

Local profiles use `api_key: not-needed`. DeepSeek uses the built-in `deepseek` provider (reads `DEEPSEEK_API_KEY` from env/profile `.env`).

---

## Hooks

### context-overflow guard

**File:** [`agents/claude-code/hooks/check-context.sh`](./agents/claude-code/hooks/check-context.sh)
**Registered in:** `~/.claude/settings.json` (see [`agents/claude-code/settings.example.json`](./agents/claude-code/settings.example.json))
**Event:** `PostToolBatch` — fires after every tool batch, before the next model call
**Gate:** only activates when `CLAUDE_LOCAL_MODEL` env var is set (by `ccornith`/`ccqwopus`/`ccqwen`)

**What it does:**
1. Exits immediately if `CLAUDE_LOCAL_MODEL` is not set (cloud sessions)
2. Queries `http://127.0.0.1:<PORT>/slots` for the active llama.cpp server
3. If context usage exceeds 85%, injects a `systemMessage` to Claude: *"Run /compact now to prevent overflow."*
4. This prevents the `exceed_context_size_error` 400 from llama.cpp

**Installation:** copy the `hooks` block from `agents/claude-code/settings.example.json` into `~/.claude/settings.json`.

---

## Prompts & Contexts

### `local-agent.md`

**File:** `agents/claude-code/prompts/local-agent.md (copy to ~/.claude/contexts/)`
**Appended by:** `ccornith`, `ccqwen`, `ccqwopus` via `--append-system-prompt-file`

```markdown
- Read partial files with offset/limit. Use LSP for navigation. Never dump full files.
- Be concise. Don't explain code unless asked.
- No subagents or task delegation.
- Never expose secrets or keys in output.
```

Keeps local model sessions efficient — avoids context bloat from verbose outputs and unnecessary subagent fanout.

---

## Environment Variables

| Variable | Set by | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | `.env` | OpenRouter API key for `claude-or`, `code` |
| `DEEPSEEK_API_KEY` | `.env` | DeepSeek API key for `hermes-ds` |
| `CLAUDE_LOCAL_MODEL` | `ccornith`/`ccqwen`/`ccqwopus` | Gates the context-overflow hook |
| `CLAUDE_LOCAL_MODEL_PORT` | `ccornith`/`ccqwen`/`ccqwopus` | Tells the hook which llama.cpp port to check |
| `LD_LIBRARY_PATH` | server helpers | Points to CUDA 12.8 libs (`$HOME/.local/cuda-12.8/lib64`) |
| `GGML_CUDA_REGISTER_HOST` | manual (patched build) | Enables mmap pinning on fable5-optimizations fork |
| `GGML_SCHED_PREFETCH_EXPERTS` | manual (patched build) | Enables MoE expert prefetch |
| `LLAMACPP_BASE_URL` | FCC proxy helpers | Points FCC to the right llama.cpp server |
| `PORT` | FCC proxy helpers | FCC proxy listen port |

---

## Scripts

| Script | Purpose |
|---|---|
| [`scripts/model-status.sh`](./scripts/model-status.sh) | Shows running servers and configured models |
| [`scripts/git-push-all`](./scripts/git-push-all) | Pushes to all remotes |
| [`yt-transcript`](./yt-transcript) | YouTube metadata + transcript (no API key) |
| `.claude/or-proxy.mjs` | OpenRouter model-name translator proxy |

---

## Installation

```bash
# Symlink the aliases file to zshrc.d
ln -sf ~/Development/ai/local-llms/patches/providers.zsh ~/.zshrc.d/providers.zsh

# Install the context-overflow hook
cp ~/Development/ai/local-llms/agents/claude-code/settings.example.json /tmp/hook-snippet.json
# Add the "hooks" section to ~/.claude/settings.json manually (merge, don't replace)

# Copy the hook script (if updating)
cp ~/Development/ai/local-llms/agents/claude-code/hooks/check-context.sh ~/.claude/hooks/

# Hermes profiles are created via `hermes profile create` — see CLAUDE.md
```

---

## How to Add a New Model

1. Download GGUF to `~/models/<name>/`
2. Add a `_ensure_<name>_server()` function in `providers.zsh`
3. Choose a free port, update the port map above
4. Add the alias function (Claude Code / OpenCode / Hermes)
5. Create a Hermes profile if needed (`hermes profile create`)
6. Update this file, CLAUDE.md, and REFERENCES.md
