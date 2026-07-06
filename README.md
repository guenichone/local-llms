# Local LLMs Setup

WSL2 + RTX 5080 (16 GB VRAM, Blackwell sm_120), CUDA 12.8, llama.cpp.

## Quick Reference

```bash
# ── Claude Code ──
claude-or                          # Opus 4.8 via OpenRouter ($)
claude-or "claude-sonnet-5" -p hi  # Sonnet 5, --print mode
claude-or-sonnet                   # Alias for Sonnet 5
claude-or-opus                     # Alias for Opus 4.8
claude-or-haiku                    # Alias for Haiku 4.5
claude-or-stop                     # Kill OpenRouter proxy

claude-local                       # Ornith Q5 (local, free, ~30s delay)
claude-local-stop                  # Kill local proxy

# ── OpenCode ──
code                               # TUI model picker
code ds                            # DeepSeek V4 Flash (OpenRouter)
code ds-pro                        # DeepSeek V4 Pro (OpenRouter)
code glm                           # GLM 5.2 (OpenRouter)
code qwen                          # Qwen 3.6 27B (OpenRouter)
code qwen-coder                    # Qwen 3 Coder Plus (OpenRouter)
code ornith                        # Ornith Q5 (local llama.cpp)
code local                         # Qwen3.6-27B MTP (local llama.cpp)

# ── Ornith Server ──
llama-server \
  -m ~/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf \
  -ngl 99 -t 8 -c 131072 --port 8082 --host 127.0.0.1 \
  --temp 0.6 --top-p 0.95 --top-k 20 \
  -ub 1024 -b 1024 --cache-reuse 256 \
  --flash-attn on \
  --reasoning-preserve \
  --cache-type-k q4_0 --cache-type-v q4_0

# ── Hermes Agent ──
hermes config set provider openai
hermes config set api_key not-needed
hermes config set base_url http://127.0.0.1:8082/v1
hermes config set model /home/barrak/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf

# ── Utilities ──
yt-transcript <video-id>            # YouTube transcript with timestamps
yt-transcript <video-id> --text     # Plain text only
```

## Shell Aliases

Defined in `~/.zshrc.d/providers.zsh` (sourced from `.zshrc`).

### `claude-or` — Claude Code via OpenRouter

Runs Claude Code through a local proxy that translates model names to OpenRouter format.

| Argument | OpenRouter Model |
|---|---|
| `claude-opus-4-8` (default) | `anthropic/claude-opus-4.8` |
| `claude-sonnet-5` | `anthropic/claude-sonnet-5` |
| `claude-haiku-4-5` | `anthropic/claude-haiku-4.5` |
| `claude-fable-5` | `anthropic/claude-fable-5` |

The proxy (`~/.claude/or-proxy.mjs`) runs on `localhost:8099`. Reads `OPENROUTER_API_KEY` from `.env`.

### `claude-local` — Claude Code via Local Ornith

Anthropic protocol proxy via free-claude-code (fcc). Auto-starts Ornith llama-server on `:8082` and fcc-server proxy on `:8097`.

- Proxy: `fcc-server` on `localhost:8097` (llama.cpp backend at `localhost:8082`)
- Supports tool calls (passed through to Ornith; may or may not work depending on complexity)
- Streams Anthropic SSE format properly
- Uses dummy `fcc-no-auth` key (proxy ignores it)
- Known limitation: ~30s TTFT due to Ornith's `<think>` reasoning step

### `code` — OpenCode via OpenRouter

Quick model selector. Tab completions available.

| Shortcut | Model |
|---|---|
| `ds`, `dsf`, `ds-flash`, `deepseek-v4-flash` | DeepSeek V4 Flash (OpenRouter) |
| `dsp`, `ds-pro`, `deepseek-v4-pro` | DeepSeek V4 Pro (OpenRouter) |
| `glm`, `glm5` | GLM 5.2 (OpenRouter) |
| `qwen`, `qwen3.6` | Qwen 3.6 27B (OpenRouter) |
| `qwen-flash`, `qwf` | Qwen 3.6 Flash (OpenRouter) |
| `qwen-coder`, `qwc` | Qwen 3 Coder Plus (OpenRouter) |
| `ornith` | Ornith-1.0-9B Q5_K_M (local) |
| `local` | Qwen3.6-27B MTP (local) |
| *(any other)* | passed as `openrouter/<name>` |

### `yt-transcript`

Fetches YouTube transcripts. Uses `yt-dlp` under the hood.

```bash
yt-transcript <video-id-or-url>          # with timestamps
yt-transcript <video-id-or-url> --text   # plain text only
yt-transcript <video-id-or-url> --lang es
```

## Proxies

### OpenRouter Proxy (`~/.claude/or-proxy.mjs`)

Strips `[1m]` suffixes from Claude Code's internal model names and maps them to OpenRouter paths.

- Port: `8099`
- Reads `OPENROUTER_API_KEY` from `.env` in priority order: proxy dir → parent → CWD
- Passes through streaming responses unchanged
- Only translates model name in request body; response passes through

### Local Proxy — free-claude-code (`fcc-server`)

[free-claude-code](https://github.com/Alishahryar1/free-claude-code) is a full Anthropic Messages API → OpenAI Chat Completions proxy. Supports tool calls, model discovery, streaming, and admin UI.

- Port: `8097`
- Backend: llama.cpp at `http://127.0.0.1:8082/v1`
- Model: `anthropic/llamacpp/ornith-1.0-9b-Q5_K_M.gguf` (also available as "no thinking" variant)
- Admin UI: `http://127.0.0.1:8097/admin` (local only)
- Installed via `uv tool install` with Python 3.14.4 (asdf)
- Runs `fcc-server` with env vars `PORT`, `LLAMACPP_BASE_URL`, `MODEL`
- Client: `fcc-claude` — wraps Claude Code CLI

## Benchmarks

All benchmarks run via `benchmarks/coding_benchmark.py` — 11 tasks across code generation, debugging, refactoring, testing, security, and optimization. Non-streaming, `max_tokens=4096`, `temp=0.6`.

### Results (RTX 5080, CUDA 12.8)

| Quant | Prompt t/s | Gen t/s | TTFT | Size | Bug-finding Quality |
|---|---|---|---|---|---|
| **Q5_K_M** | **1,585** | **117** | **29s** | **6.1 GB** | **Found all bugs ✓** |
| Q4_K_M* | 725 | 123 | 23s | 5.3 GB | Missed bugs ✗ |
| Q6_K | 970 | 48 | 57s | 7.2 GB | Good, but 2.4x slower |
| NVFP4-MTP | 751 | 76 | 49s | 5.1 GB | 3/11 tasks empty output ✗ |

*\*Q4_K_M run on CUDA 13.3 (broken MMQ on Blackwell, cuBLAS fallback ~5x slower prompt)*

### Verdict: Q5_K_M is the sweet spot

- Best quality-to-speed ratio
- Most reliable bug finding (found all bugs in merge_intervals + thread-safety + security)
- Zero empty outputs (Q4 sometimes, NVFP4 often produced empty content)
- Fits easily in 16 GB VRAM with 131K context + KV cache quant

### Why not other quants

| Quant | Issue |
|---|---|
| Q4_K_M | Lower quality, missed subtle bugs (reference mutation, empty guard) |
| Q6_K | Gen speed cratered to 48 t/s — 6-bit format has inefficient GPU kernels on NVIDIA |
| NVFP4-MTP | Unoptimized llama.cpp kernels + MTP overhead = slower AND worse quality |
| Q8_0 | Would be ~9.7 GB — doesn't fit with 131K context in 16 GB VRAM |

## Hardware

| Component | Spec |
|---|---|
| GPU | NVIDIA GeForce RTX 5080 16 GB VRAM (Blackwell SM 12.0) |
| CPU | AMD Ryzen 7 9800X3D |
| RAM | 32 GB Windows / 15 GB WSL allocation |
| OS | WSL2 — Ubuntu 24.04 LTS |
| CUDA | 12.8.61 (for builds) + 13.3 (system, for other tools) |

## CUDA Build Notes

### The Blackwell MMQ Bug

CUDA 13.1+ has a known MMQ kernel codegen bug on Blackwell sm_120 — `mul_mat_q` int8 MMA write-back epilogue produces out-of-range shared-memory stores. This causes intermittent crashes and silent fallback to cuBLAS (5-6x slower prompt).

**Fix:** Install CUDA 12.8 alongside 13.3 and rebuild llama.cpp with it.

### Build Commands

```bash
export PATH=$HOME/.local/cuda-12.8/bin:$PATH
export LD_LIBRARY_PATH=$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH

cd ~/llama.cpp && rm -rf build
cmake -B build \
  -DGGML_CUDA=ON \
  -DGGML_FLASH_ATTN=ON \
  -DGGML_CUDA_FORCE_CUBLAS=OFF \
  -DCMAKE_CUDA_ARCHITECTURES="120" \
  -DCUDAToolkit_ROOT=$HOME/.local/cuda-12.8
cmake --build build --config Release -j $(nproc)
```

## Environment Variables

Required in `~/Development/local-llms/.env`:

```bash
OPENROUTER_API_KEY=sk-or-...     # Required for claude-or, code (OpenRouter models)
DEEPSEEK_API_KEY=sk-...           # Optional — direct DeepSeek API
HF_TOKEN=hf_...                   # Required for gated models (Gemma)
```

## Models

| Model | Size | Quant | Location |
|---|---|---|---|
| Ornith-1.0-9B | 9B | Q5_K_M (6.1 GB) | `~/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf` |
| Ornith-1.0-9B | 9B | Q4_K_M (5.3 GB) | `~/models/ornith-1.0-9b/ornith-1.0-9b-Q4_K_M.gguf` |
| Qwen3.6-27B MTP | 27B | Q3_K_S (12 GB) | `~/models/qwen3.6-27b-mtp-Q3_K_S.gguf` |
| Qwen3.5-27B | 27B | Q4_K_M (17 GB) | `~/models/qwen3.5-27b/Qwen_Qwen3.5-27B-Q4_K_M.gguf` |
| Gemma 4 E4B | 4B | Q4_K_M (3 GB) | `~/models/gemma4-4b/gemma-4-E4B-it-Q4_K_M.gguf` |
| Gemma 4 31B QAT | 31B | Q4_0 (17 GB) | Windows LM Studio (too large for 16 GB VRAM) |

## Ornith Knowledge

Key findings from [How to Run Ornith 1.0 Locally](https://codersera.com/blog/how-to-run-ornith-1-0-locally-2026/):

### Model Architecture
- Ornith is **post-trained on Qwen 3.5** (9B, 35B MoE, 397B). The 31B variant (Gemma 4-based) has no public checkpoint yet.
- It uses Qwen-style tool calling (`qwen3_xml` format) and emits `<think>` reasoning blocks.
- Under vLLM, you need `--tool-call-parser qwen3_xml --reasoning-parser qwen3`. Under llama.cpp, `--reasoning-preserve` is the equivalent.

### Self-Scaffolding
Ornith's key innovation: during RL training, the model jointly produces solution rollouts *and* the task-specific scaffolds that guide them. The model is optimized not just to answer well but to author the orchestration that elicits the answer. Three defenses against reward hacking: fixed outer trust boundary, deterministic monitor, and frozen LLM judge.

### Token Budget
**Always set max_tokens ≥ 4096.** A code-generation prompt capped at 2048 output tokens can spend the entire budget inside the reasoning block and never reach the code. Our benchmarks confirm this — 3/11 tasks produced empty output at 4096 with NVFP4, and Ornith consistently burns ~1000+ tokens on `<think>` before answering.

### Context Window
256K theoretical, but **lower context is faster and more memory-stable.** We use 32K as the default — sufficient for agent workloads, avoids OOM on 16 GB VRAM with KV cache quant.

### Agent Compatibility
Officially tested: Claude Code, OpenHands, OpenClaw, Hermes Agent, opencode. Any tool accepting an OpenAI-compatible base URL can use it.

### Benchmark Reality
| Model | Terminal-Bench | SWE-Bench Verified | Notes |
|---|---|---|---|
| Ornith 397B | 77.5 | 82.4 | Edges Opus 4.7, trails Opus 4.8 |
| **Ornith 35B MoE** | **64.2** | **75.6** | **Best local variant, beats Qwen 3.5-397B** |
| Ornith 9B | 43.1 | 69.4 | Respectable triage model |
| Qwen 3.6-35B | 52.5 | 73.4 | Reference baseline |

The 35B MoE is the standout — but needs ~25 GB (Q5_K_M), not viable on 16 GB RTX 5080. The 9B Q5_K_M is the right choice for our GPU.
