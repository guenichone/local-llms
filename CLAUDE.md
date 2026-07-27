# Local LLMs Setup (WSL2 + RTX 5080)

## Repo Map

This repo is split into three indexes — use the right one for what you need:

| File | Purpose | When to use |
|---|---|---|---|
| **[ALIASES.md](./ALIASES.md)** | Every alias, hook, prompt, server port, env var | "How do I launch X?" / "What port is Y on?" / "Where's the hook script?" |
| **[REFERENCES.md](./REFERENCES.md)** | External sources (papers, videos, blog posts, PRs, repos, models) | "Where did we learn about Bonsai?" / "What was that Codacus video?" |
| **[benchmarks/master_results.json](./benchmarks/master_results.json)** | Normalized benchmark data for all tested models | "What's the latest pp/tg for Q5_K_M?" / "Compare all models" |
| **[benchmarks/models/](./benchmarks/models/)** | Per-model knowledge files with all findings | "Show me everything about Ornith 9B" |
| **CLAUDE.md** (this file) | Operational knowledge: benchmarks, bugs, build instructions, model configs | "What's the best quant for Ornith?" / "How to rebuild llama.cpp?" / "Why is CUDA 13.3 broken?" |

Other tracked files:

| Path | What |
|---|---|
| [`patches/providers.zsh`](./patches/providers.zsh) | Shell aliases & server helpers (symlink to `~/.zshrc.d/`) |
| [`opencode.json`](./opencode.json) | OpenCode provider/model config (active, read by OpenCode) |
| [`agents/claude-code/`](./agents/claude-code/) | Claude Code reference files (hooks, prompts, settings — copy to install) |
| [`agents/hermes/profiles/`](./agents/hermes/profiles/) | Reference copies of Hermes Agent profile configs |

## Quick Reference

```bash
# ── Claude Code ──
claude-or                          # Opus 4.8 via OpenRouter ($)
claude-or-sonnet                   # Sonnet 5 via OpenRouter
claude-go                          # Claude Haiku → DeepSeek Flash ($10/mo)
claude-go-sonnet                   # Claude Sonnet → DeepSeek V4 Pro
claude-go-opus                     # Claude Opus  → Kimi K3
ccornith                           # Ornith Q5 (local, free, ~30s delay)
ccqwen                             # Qwen3.6-27B MTP (local)
ccqwopus                           # Qwopus 35B Nano (local)
ccstop                             # Kill all servers + proxies

# ── OpenCode ──
code                               # TUI model picker
code ds                            # DeepSeek V4 Flash (OpenRouter)
code ornith                        # Ornith Q5 (local llama.cpp)
code local                         # Qwen3.6-27B MTP (local)

# ── Hermes Agent ──
hermes-ornith                      # Ornith Q5 (local)
hermes-qwopus                      # Qwopus 35B Nano (local)
hermes-gemma                       # Gemma 4 E4B (local)
hermes-ds                          # DeepSeek V4 Pro (remote)
hermes-go                          # DeepSeek V4 Flash via OpenCode Go ($10/mo)

# ── Utilities ──
yt-transcript <video-id>           # YouTube transcript
```

## Documentation & References

### Ornith-1.0
- [Official Ornith Site](https://www.ornith.site/)
- [Ornith 1.0 Technical Write-up](https://deep-reinforce.com/ornith_1_0.html)
- [How to Run Ornith 1.0 Locally (Codersera)](https://codersera.com/blog/how-to-run-ornith-1-0-locally-2026/) — covers Ollama, LM Studio, vLLM, agent wiring, tool parsers, quant picks
- [Ornith on Hugging Face](https://huggingface.co/collections/deepreinforce-ai/ornith-10)
- [Ornith 9B GGUF (bartowski)](https://huggingface.co/bartowski/deepreinforce-ai_Ornith-1.0-9B-GGUF) — our source for Q4/Q5/Q6 GGUF files
- [Ornith NVFP4 MTP (s-batman)](https://huggingface.co/s-batman/Ornith-1.0-9B-NVFP4-MTP-GGUF) — native Blackwell format (tested, worse than Q5_K_M)
- [llama.cpp MTP Issue #24399](https://github.com/ggml-org/llama.cpp/issues/24399) — Blackwell sm_120 MMQ kernel bug

### Tools & Frameworks
- [OpenCode](https://opencode.ai) — our primary agent framework
- [Hermes Agent](https://github.com/NousResearch/Hermes-Agent) — tested harness for Ornith
- [llama.cpp](https://github.com/ggml-org/llama.cpp) — inference engine
- [free-claude-code](https://github.com/Alishahryar1/free-claude-code) — Anthropic→OpenAI proxy (installed via uv, Python 3.14.4)
- [CUDA 12.8 Archive](https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda_12.8.0_570.86.10_linux.run)

### Related Guides
- [Qwen 3.6 Local Setup](https://codersera.com/blog/how-to-run-qwen-3-6-locally-2026/) — closely related (Ornith is post-trained on Qwen)
- [Open-Source LLMs Landscape 2026](https://codersera.com/blog/open-source-llms-landscape-2026/)
- [Best Free Local LLM Tools 2026](https://codersera.com/blog/best-free-local-llm-tools-2026/)

## Provider Aliases

Shell aliases defined in `~/.zshrc.d/providers.zsh` (sourced from `.zshrc`). API keys in `.env`.

| Command | What | Proxy | Port | Key Source |
|---|---|---|---|---|
| `claude-or` | Claude Code → OpenRouter | `or-proxy.mjs` | 8099 | `OPENROUTER_API_KEY` |
| `ccornith` | Claude Code → Ornith Q5 | `fcc-claude` (free-claude-code) | 8097 | `fcc-no-auth` (dummy, ignored) |
| `ccqwen` | Claude Code → Qwen3.6-27B MTP | `fcc-claude` (free-claude-code) | 8098 | `fcc-no-auth` (dummy, ignored) |
| `code` | OpenCode with model picker | none | — | `OPENROUTER_API_KEY` |

### `claude-or` — Claude Code via OpenRouter

Translates internal model names to OpenRouter format via proxy on `:8099`.

| Argument | OpenRouter Model |
|---|---|
| `claude-opus-4-8` (default) | `anthropic/claude-opus-4.8` |
| `claude-sonnet-5` | `anthropic/claude-sonnet-5` |
| `claude-haiku-4-5` | `anthropic/claude-haiku-4.5` |
| `claude-fable-5` | `anthropic/claude-fable-5` |

### `ccornith` — Claude Code via Local Ornith

Anthropic protocol proxy via free-claude-code (fcc). Auto-starts Ornith llama-server on `:8082` and fcc-server proxy on `:8097`. Uses `--reasoning-preserve` to capture `<think>` blocks. Supports tool calls (passed through to local model; Ornith may or may not handle them depending on complexity). Uses dummy `fcc-no-auth` key (proxy ignores it).

### `ccqwen` — Claude Code via Local Qwen 3.6 27B MTP

Same proxy approach as Ornith. Auto-starts Qwen llama-server on `:8080` and fcc-server proxy on `:8098`. MTP speculative decoding gives ~2x generation speed (~96 t/s vs ~48).

### `code` — OpenCode

| Shortcut | Model |
|---|---|
| `ds`, `dsf`, `ds-flash` | DeepSeek V4 Flash (OpenRouter) |
| `dsp`, `ds-pro` | DeepSeek V4 Pro (OpenRouter) |
| `glm`, `glm5` | GLM 5.2 (OpenRouter) |
| `qwen`, `qwen3.6` | Qwen 3.6 27B (OpenRouter) |
| `qwen-flash`, `qwf` | Qwen 3.6 Flash (OpenRouter) |
| `qwen-coder`, `qwc` | Qwen 3 Coder Plus (OpenRouter) |
| `ornith` | Ornith-1.0-9B Q5_K_M (local llama.cpp) |
| `local` | Qwen3.6-27B MTP (local llama.cpp) |
| *(any other)* | `openrouter/<name>` |

## Hardware

- **GPU:** NVIDIA GeForce RTX 5080 16GB VRAM (Blackwell SM 12.0)
- **CPU:** AMD Ryzen 7 9800X3D
- **RAM:** 32GB Windows / 15GB WSL allocation
- **OS:** WSL2 — Ubuntu 24.04 LTS
- **CUDA Driver:** 13.3 (system); 12.8.61 (llama.cpp builds)

## CUDA Build & Blackwell Tuning

### The Blackwell MMQ Bug (CUDA 13.1+)

Confirmed sm_120 bugs (see [llama.cpp #24399](https://github.com/ggml-org/llama.cpp/issues/24399)):
- `mul_mat_q<Q8_0>` — out-of-range shared store (crash after ~hundreds of gens)
- `flash_attn_ext_f16` — flash attention kernel crash
- cuBLASLt TF32 split-k — barrier mismatch

**Fix:** Install CUDA 12.8 alongside 13.3 and rebuild llama.cpp with it.

### Installation

```bash
# Install CUDA 12.8 (coexists with 13.3)
wget https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda_12.8.0_570.86.10_linux.run
chmod +x cuda_12.8.0_570.86.10_linux.run
./cuda_12.8.0_linux.run --silent --toolkit --toolkitpath=$HOME/.local/cuda-12.8 --nox11

# Rebuild llama.cpp
cd ~/llama.cpp && rm -rf build
export PATH=$HOME/.local/cuda-12.8/bin:$PATH
cmake -B build \
  -DGGML_CUDA=ON \
  -DGGML_FLASH_ATTN=ON \
  -DGGML_CUDA_FORCE_CUBLAS=OFF \
  -DCMAKE_CUDA_ARCHITECTURES="120" \
  -DCUDAToolkit_ROOT=$HOME/.local/cuda-12.8
cmake --build build --config Release -j $(nproc)
```

Always run with `LD_LIBRARY_PATH=$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH`.

### Fable 5 Optimizations (Jul 2026)

Based on the [I Asked Claude Fable 5 to Improve llama.cpp](https://www.youtube.com/watch?v=VytSYCDhWQ0) experiment by TheCodacus. We applied the 2 winning optimizations from their [fork](https://github.com/thecodacus/llama.cpp) (branches `fable5/host-register`, `fable5/prefetch-experts`).

Our fork with the patches: [guenichone/llama.cpp:fable5-optimizations](https://github.com/guenichone/llama.cpp/tree/fable5-optimizations)

#### Optimizations Applied

| # | Optimization | What It Does | Env Var | Status |
|---|---|---|---|---|
| 1 | **Mmap pinning** | `cudaHostRegister` the mmap'd CPU weight pages for faster H2D transfers | `GGML_CUDA_REGISTER_HOST=1` | Working |
| 2 | **Expert prefetch** | Upload full MoE expert tensors through 2nd backend instance overlapping with compute | `GGML_SCHED_PREFETCH_EXPERTS=N` | Working |
| 3 | Adaptive spec controller | Dynamically adjust draft length for offloaded MoE | — | Lost (author's finding) |
| 4 | CPU+GPU split work | Split expert work between CPU and GPU on same layer | — | Lost (PCIe bottleneck) |

#### Benchmark Results — Ornith 9B Q5_K_M (RTX 5080, CUDA 12.8)

| Scenario | Vanilla (t/s) | Patched (t/s) | Speedup |
|---|---|---|---|
| `-ngl 0` (all CPU) pp512 | 751 | **1,771** | **+135%** |
| `-ngl 0` (all CPU) tg128 | 6.72 | 6.93 | +3% |
| `-ngl 20` (partial) pp512 | 2,077 | **3,257** | **+57%** |
| `-ngl 20` (partial) tg128 | 17.51 | 17.47 | same |
| `-ngl 99` (all GPU) pp512 | 5,935 | 5,812 | -2% |
| `-ngl 99` (all GPU) tg128 | 107.40 | 108.03 | +0.6% |

**Key findings:**
- Mmap pinning gives **massive gains when weights are in system RAM** (all/partial offload)
- No change on fully GPU-resident models (expected — no H2D copies)
- Decode speed unaffected (expected — decode runs on device holding the weights)
- Output verified **token-identical** to vanilla llama.cpp

#### Building the Patched Version

```bash
cd ~/llama.cpp
git checkout fable5-optimizations
export PATH=$HOME/.local/cuda-12.8/bin:$PATH
cmake -B build-patched \
  -DGGML_CUDA=ON -DGGML_FLASH_ATTN=ON \
  -DCMAKE_CUDA_ARCHITECTURES="120" \
  -DCUDAToolkit_ROOT=$HOME/.local/cuda-12.8 \
  -DGGML_CUDA_FULL_MMVQ=OFF \
  -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-rpath,$HOME/.local/cuda-12.8/lib64" \
  -DCMAKE_EXE_LINKER_FLAGS="-Wl,-rpath,$HOME/.local/cuda-12.8/lib64"
cmake --build build-patched --config Release -j $(nproc)
```

#### Running with Optimizations

```bash
export LD_LIBRARY_PATH=$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH

# Mmap pinning only (works on any model with partial offload)
GGML_CUDA_REGISTER_HOST=1 ~/llama.cpp/build-patched/bin/llama-server \
  -m ~/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf \
  -ngl 99 --port 8082 --host 127.0.0.1

# MoE expert prefetch (requires MoE model with offloaded layers)
GGML_SCHED_PREFETCH_EXPERTS=3 GGML_CUDA_REGISTER_HOST=1 \
  ~/llama.cpp/build-patched/bin/llama-cli \
  -m ~/models/qwen3.6-35b-a3b/Qwen_Qwen3.6-35B-A3B-IQ3_XXS.gguf \
  -ngl 20 -ncmoe 26 -p "Write fibonacci..."
```

#### Subagent Code Review Findings

Our subagent found and we fixed:
- **HIGH**: Missing bounds check in `register_host()` (could pass OOB pointer to `cudaHostRegister`)
- **MEDIUM**: `prefetch_used` array not fully reset on slot count reduction
- **LOW**: `prefetch_cur` not reset on disable

## Models

| Model | Size | Quant | Location | Notes |
|---|---|---|---|---|
| Qwen3.6-27B-MTP | 27B | Q3_K_S (12 GB) | `~/models/qwen3.6-27b-mtp-Q3_K_S.gguf` | MTP heads, ~2x gen speedup |
| Qwen3.5-27B | 27B | Q4_K_M (17 GB) | `~/models/qwen3.5-27b/Qwen_Qwen3.5-27B-Q4_K_M.gguf` | Standard, no MTP |
| **Ornith-1.0-9B** | **9B** | **Q5_K_M (6.1 GB)** | `~/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf` | **Default coding agent** |
| Ornith-1.0-9B (fallback) | 9B | Q4_K_M (5.3 GB) | `~/models/ornith-1.0-9b/ornith-1.0-9b-Q4_K_M.gguf` | Faster, lower quality |
| Gemma 4 E4B | 4B | Q4_K_M (3 GB) | `~/models/gemma4-4b/gemma-4-E4B-it-Q4_K_M.gguf` | Fast, CPU-friendly |
| Gemma 4 31B QAT | 31B | Q4_0 (17 GB) | `C:/Users/.../lmstudio-community/gemma-4-31B-it-QAT-GGUF/` | Needs `-ngl 30` on 16GB |
| Qwen3.6-35B-A3B MoE | 35B (3B active) | IQ3_XXS (15.8 GB) | `~/models/qwen3.6-35b-a3b/` | MoE, 256 experts, for prefetch bench |

## Ornith Knowledge

### Model Architecture (from [Codersera Guide](https://codersera.com/blog/how-to-run-ornith-1-0-locally-2026/))

- **Base:** Post-trained on **Qwen 3.5** (9B Dense, 35B MoE, 397B MoE). 31B Dense (Gemma 4) has no public checkpoint.
- **Self-scaffolding:** Key innovation — during RL, the model jointly produces solution rollouts *and* the task-specific scaffolds that guide them. Optimized not just to answer well but to author the orchestration. Three defenses against reward hacking: fixed outer trust boundary, deterministic monitor, frozen LLM judge.
- **Format:** Qwen-style tool calling (`qwen3_xml`) and `<think>` reasoning blocks. Under vLLM: `--tool-call-parser qwen3_xml --reasoning-parser qwen3`. Under llama.cpp: `--reasoning-preserve`.
- **Context:** 256K theoretical. We use **131K** for coding agents (Hermes Agent can use 32K for faster response).
- **Token Budget:** **Always set max_tokens ≥ 4096.** Ornith burns ~1000+ tokens on `<think>` before answering. At 2048 it can spend the entire budget thinking and produce zero visible output (confirmed by our own benchmarks).

### Quant Comparison (RTX 5080, CUDA 12.8, 11-task benchmark)

| Quant | Prompt t/s | Gen t/s | TTFT | Size | Quality |
|---|---|---|---|---|---|
| **Q5_K_M** | **1,585** | **117** | **29s** | 6.1 GB | Best: found all bugs, 0 empty outputs |
| Q4_K_M* | 725 | 123 | 23s | 5.3 GB | Missed subtle bugs |
| Q6_K | 970 | 48 | 57s | 7.2 GB | 6-bit kernel inefficient on NVIDIA |
| NVFP4-MTP | 751 | 76 | 49s | 5.1 GB | 3/11 tasks empty, slower kernels |

*\*Q4_K_M tested on CUDA 13.3 (broken MMQ → cuBLAS fallback, ~5x slower prompt)*

**Verdict: Q5_K_M is the sweet spot.** NVFP4 kernels not optimized; Q6 6-bit format has poor GPU kernel support; Q4 misses bugs.

### Official Benchmark Data (from [DeepReinforce](https://deep-reinforce.com/ornith_1_0.html))

| Model | Terminal-Bench | SWE-Bench Verified | Notes |
|---|---|---|---|
| Ornith 397B | 77.5 | 82.4 | Edges Opus 4.7, trails Opus 4.8 & GLM-5.2-744B |
| **Ornith 35B MoE** | **64.2** | **75.6** | **Standout local variant — beats Qwen 3.5-397B** |
| Ornith 9B | 43.1 | 69.4 | Respectable triage, ~6GB at Q4 |
| Qwen 3.6-35B | 52.5 | 73.4 | Reference baseline |

35B MoE is the sweet spot for 24GB GPUs. Not viable on our 16GB — 9B Q5_K_M is the right choice.

## Inference Commands

### Server Commands (llama-server)

#### Ornith Q5 (primary coding agent, port 8082)

```bash
export LD_LIBRARY_PATH=$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH
llama-server \
  -m ~/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf \
  -ngl 99 -t 6 -c 200000 --port 8082 --host 127.0.0.1 \
  --temp 0.6 --top-p 0.95 --top-k 20 \
  -ub 4096 -b 4096 --cache-reuse 256 \
  --flash-attn on --reasoning-preserve \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  -np 6 --kv-unified
```

Flag details:
| Flag | Effect |
|---|---|
| `-t 6` | Optimal thread count (benchmarked: t=6 > t=8 for Ornith) |
| `-ub 4096 -b 4096` | Large batches for prompt processing |
| `--cache-reuse 256` | KV cache prefix reuse (agent workloads) |
| `--flash-attn on` | Flash Attention +15% pp, +5% tg on vanilla build |
| `--reasoning-preserve` | Preserve `<think>` blocks as separate field (Qwen-style) |
| `--cache-type-k/v q8_0` | KV cache quant → better precision (uses ~3.3 GB more VRAM vs q4_0) |
| `-np 6 --kv-unified` | 6 parallel slots with unified KV cache |
| `--reasoning-budget N` | Cap thinking tokens (default -1 = unlimited; 2048 recommended) |
| `enableAgentSafetyClassifier` | Set `false` in `~/.claude/settings.json` to disable the safety classifier (circumvents timeout with slow local models) |

#### Qwen3.6-27B MTP — Turboquant build (port 8080)

```bash
# Uses turboquant build with turbo3 KV cache to fit 200K ctx on single 5080
export LD_LIBRARY_PATH=$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH
$HOME/llama-cpp-turboquant/build-turbo/bin/llama-server \
  -m ~/models/qwen3.6-27b-mtp-Q3_K_S.gguf \
  -t 4 -c 200000 --port 8080 --host 127.0.0.1 \
  --temp 0.7 --top-p 0.95 --top-k 40 \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  --flash-attn on \
  -ctk q8_0 -ctv turbo3 \
  -np 1
```

Key: `--fit on` (default in turboquant build) auto-determines GPU layer distribution. `-np 1` gives the single slot full 200K context (no splitting). `--cache-reuse` is disabled by MTP — no point adding it. `-t 4` is optimal for generation speed.

**Context/speed tradeoff** (turboquant build, turbo3 KV, single 5080):

| Context | KV cache type | Speed | VRAM used |
|---|---|---|---|
| 55K | q4_0 (vanilla build) | ~60 t/s | ~15 GB |
| 131K | turbo3 | ~17 t/s | ~15 GB |
| **200K** | **turbo3** | **~10 t/s** | **~14.6 GB** |

turbo3 compresses the KV cache (not the model), enabling 200K context on a single 16 GB GPU. Speed drops at larger contexts because attention must scan more KV entries per token. MTP adds ~700 MB VRAM overhead.

### CLI Commands (llama-cli)

```bash
# Ornith Q5 — single turn
~/llama.cpp/build/bin/llama-cli \
  -m ~/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf \
  -ngl 99 -t 8 -n 256 --temp 0.6 \
  --single-turn --no-display-prompt \
  --prompt "<|im_start|>user\nYour prompt<|im_end|>\n<|im_start|>assistant\n"

# Qwen3.6-27B MTP — single turn with speculative decoding
~/llama.cpp/build/bin/llama-cli \
  -m ~/models/qwen3.6-27b-mtp-Q3_K_S.gguf \
  -ngl 99 -t 8 -n 256 --temp 0.7 \
  --single-turn --no-display-prompt \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  --prompt "<|im_start|>user\nYour prompt<|im_end|>\n<|im_start|>assistant\n"

# Gemma 4 E4B — needs --chat-template gemma
~/llama.cpp/build/bin/llama-cli \
  -m ~/models/gemma4-4b/gemma-4-E4B-it-Q4_K_M.gguf \
  --chat-template gemma \
  -ngl 99 -t 8 -n 256 --temp 0.7 \
  --single-turn --no-display-prompt \
  --prompt "Your prompt"
```

## Agent Integration

### OpenCode

Agent profiles defined in `opencode.json` and `.opencode/agents/`:

```bash
opencode run --agent ornith-coder "Your task"   # coding agent
opencode run --agent ornith-reviewer "Review"    # code review subagent
```

- **`ornith-coder`** (`~/.config/opencode/agents/ornith-coder.md`): primary agent, temp 0.6, all tools, 131K ctx
- **`ornith-reviewer`** (`.opencode/agents/ornith-reviewer.md`): subagent, temp 0.2, read-only + git diff/log
- **MCP:** `firecrawl` (removed — fcc proxy auto-intercept handles web search/fetch natively via DuckDuckGo/HTTP)

### Claude Code (Local)

```bash
ccornith                          # Ornith Q5 (interactive, auto-starts server + proxy)
ccornith -p "write fibonacci" --print  # non-interactive
ccqwen                            # Qwen3.6-27B MTP (interactive, auto-starts server + proxy)
ccqwen -p "write fibonacci" --print    # non-interactive
```

Anthropic protocol proxy via free-claude-code (fcc) on `:8097` (Ornith) / `:8098` (Qwen) converts Anthropic Messages API to OpenAI Chat Completions for llama.cpp. Tool calls are supported (passed through; Ornith may or may not handle them). Uses dummy `fcc-no-auth` key (proxy ignores it).

**Web Search:** Claude Code's built-in `WebSearch` requires Anthropic search backend (fails with dummy key); `Fetch` tool works fine. fcc auto-intercepts `web_search`/`web_fetch` server-side when `ENABLE_WEB_SERVER_TOOLS=true` + `FCC_AUTO_INTERCEPT_WEB_TOOLS=true` — search via DuckDuckGo, fetch via HTTP.

**Limitations:** ~30s TTFT from Ornith reasoning; tool calls stripped; quality well below Claude models. Best as a fallback when OpenRouter is unavailable.

### Hermes Agent

```bash
hermes config set provider openai
hermes config set api_key not-needed
hermes config set base_url http://127.0.0.1:8082/v1
hermes config set model /home/barrak/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf
```

Ornith is [officially listed](https://codersera.com/blog/how-to-run-ornith-1-0-locally-2026/) as a tested harness for Hermes Agent.

#### OpenCode Go (subscription)

```bash
hermes-go                          # DeepSeek V4 Flash via OpenCode Go ($10/mo)
```

Uses `provider: openai` pointing at `https://opencode.ai/zen/go/v1`. Requires `OPENCODE_GO_API_KEY` in `.env`. Same subscription as `claude-go`.

## Performance (RTX 5080)

### llama-bench — July 2026 (CUDA 12.8, vanilla build, fully GPU-resident)

| Model | Threads | Flash-Attn | pp512 t/s | tg128 t/s | Notes |
|---|---|---|---|---|---|
| **Ornith 9B Q5_K_M** | **6** | **on** | **6,044** | **131.4** | Best: vanilla build, t=6 optimal |
| Ornith 9B Q5_K_M | 8 | on | 5,742 | 123.5 | tg drops at higher threads |
| Ornith 9B Q5_K_M | 6 | off | 5,243 | 125.2 | FA gives +15% pp |
| Qwen 27B Q3_K_S | 8 | on | 1,692 | 47.4 | Best pp at t=8 |
| Qwen 27B Q3_K_S | 4 | on | 1,611 | 48.3 | Best tg at t=4 |
| Qwen 27B Q3_K_S + MTP | 4 | on | — | **~60** | turboquant, turbo3 KV, 55K ctx (measured Jul 20) |
| Qwen 27B Q3_K_S + MTP | 4 | on | — | **~17** | turboquant, turbo3 KV, 131K ctx |
| Qwen 27B Q3_K_S + MTP | 4 | on | — | **~10** | turboquant, turbo3 KV, 200K ctx |

Note: The old ~96 t/s MTP estimate was from small-context benchmarking. Real server speed at depth is 10-60 t/s depending on context size. `--no-kv-offload` caused 3.2x slowdown (48→15 t/s) — avoid it.

### Patched build (fable5-optimizations)

| Model | Threads | pp512 t/s | tg128 t/s | vs Vanilla |
|---|---|---|---|---|
| Ornith 9B Q5_K_M | 6 | 6,346 | 127.5 | pp +16%, tg same |
| Qwen 27B Q3_K_S | 8 | 1,786 | 47.7 | pp +5.6%, tg same |

**Critical:** Patched build requires `GGML_CUDA_REGISTER_HOST=1` or decode collapses to <2 t/s. Vanilla build + flash-attn is best for fully GPU-resident models (Ornith). Patched build better for partial offload.

### Cache type impact (Ornith Q5, patched + RH)

| Cache K/V | pp512 t/s | tg128 t/s |
|---|---|---|
| f16 (default) | 5,621 | 128.2 |
| q8_0 | 5,453 | 126.3 |
| q4_0 | 5,492 | 121.8 |

### Older benchmarks (CUDA 12.8, 11-task)

| Model | Prompt t/s | Gen t/s | Notes |
|---|---|---|---|
| Ornith-1.0-9B Q5_K_M | 1,585 | 117 | CUDA 12.8, flash-attn, 11-task benchmark |
| Ornith-1.0-9B Q4_K_M | 254 | 120 | CLI mode w/ KV cache |
| Gemma 4 E4B (4B) | 184 | 149 | All layers on GPU |
| Qwen3.6-27B (+ MTP) | 109 | 98 | ~2x gen speedup |
| Gemma 4 31B QAT (31B, -ngl 30) | 16 | 3.2 | Partial offload, 17GB > 16GB |

## Coding Benchmarks (Jul 5-6 2026)

### CUDA 13.3 vs 12.8 — 6 tasks, Q4_K_M

Ornith-1.0-9B Q4_K_M, non-streaming, max_tokens=4096:

| Task | 13.3 pp t/s | 12.8 pp t/s | Speedup | Quality change |
|---|---|---|---|---|
| Fibonacci | 109 | 417 | **3.8x** | same (good) |
| JSON Validator | 645 | 1,167 | **1.8x** | same (hit max_tokens) |
| Bug finding | 731 | 1,860 | **2.5x** | "no bugs" → **3 bugs found** |
| Refactor eval | 336 | 1,715 | **5.1x** | both solid |
| Test writing | 1,895 | 3,081 | **1.6x** | both good |
| API handler | 632 | 1,273 | **2.0x** | both good |
| **Average** | **725** | **1,585** | **2.2x** | quality improved |

Gen speed: 122.6 → 117.2 t/s (slight dip from KV cache quant).

### Full 11-task comparison — Q4 vs Q5 vs Q6 vs NVFP4

All on CUDA 12.8 with flash-attn, KV cache q4_0:

| Quant | Prompt t/s | Gen t/s | TTFT | Output tok | Empty outputs | Bug-finding |
|---|---|---|---|---|---|---|
| Q4_K_M* | 725 | 123 | 23s | 2,653 | 0 | Missed all |
| **Q5_K_M** | **1,585** | **117** | **29s** | 3,361 | 0 | **Found all** |
| Q6_K | 970 | 48 | 57s | 2,571 | 0 | Good but 2.4x slower |
| NVFP4-MTP | 751 | 76 | 49s | 3,304 | 3/11 | **Empty** |

*\*Q4_K_M run on CUDA 13.3 (broken MMQ)*

### Key Findings

1. **CUDA 12.8 rebuild is essential on Blackwell** — 2.2x faster prompt, fixes bug-finding quality (broken MMQ → silent cuBLAS fallback was missing bugs)
2. **Q5_K_M is the sweet spot** — best quality-to-speed ratio, zero empty outputs, all bugs found
3. **NVFP4 kernels are unoptimized** in llama.cpp — slower AND worse quality than Q4_K_M
4. **Q6 6-bit format has inefficient GPU kernels** — 60% gen speed drop for 18% more model size
5. **Ornith needs max_tokens ≥ 4096** — reasoning burns ~1000+ tokens in `<think>` blocks before any visible output

## Known Issues

- **`--chat-template` + `--prompt`** can trigger interactive mode; use `--single-turn` to force single response
- **WSL memory** fixed at 15GB allocation — large models may need swap or partial GPU offload
- **zsh compinit error** (`no such file or directory: /usr/share/zsh/vendor-completions/_docker`): broken symlink from Docker Desktop WSL integration. Fix: `sudo rm /usr/share/zsh/vendor-completions/_docker`
- **Ornith TTFT** averages ~29s due to `<think>` reasoning blocks — normal for reasoning model class
- **CUDA 13.2 with Qwen MTP** causes output corruption; use 13.1 or 13.3+
- **Gemma models need `HF_TOKEN`** env var (gated repos on HuggingFace)
- **LLAMACPP_BASE_URL must include `/v1` suffix** — fcc's Anthropic transport appends `/messages` to base URL. `http://127.0.0.1:8082/v1` → `http://127.0.0.1:8082/v1/messages` ✓; `http://127.0.0.1:8082` → `http://127.0.0.1:8082/messages` ✗ (404). Kill old fcc-server process to pick up config changes.
- **Session model path warning** — Claude Code warns `unknown session model` when session history `.jsonl` in `~/.claude/projects/` contains full GGUF paths. Fix: `sed -i 's|/home/barrak/models/ornith-1\.0-9b/ornith-1\.0-9b-Q5_K_M\.gguf|ornith-1.0-9b-Q5_K_M.gguf|g' ~/.claude/projects/*.jsonl`
- **Fable5 patched build breaks without `GGML_CUDA_REGISTER_HOST=1`** — decode speed collapses from ~125 t/s to <2 t/s on fully GPU-resident models. Always export this env var when using the patched build.
- **Only one model fits in VRAM** — Qwen 27B (12 GB) + Ornith 9B (6 GB) = 18 GB > 16 GB. `ccornith`/`ccqwen` auto-kill the other server on switch.
- **Qwen 27B config** — Uses turboquant build with `-ctk q8_0 -ctv turbo3` for 200K context on single 5080. `--no-kv-offload` causes 3.2x slowdown — avoid it. Vanilla build limited to ~55K ctx without turbo3. `--cache-reuse` is disabled by MTP.
- **FCC proxy model display** — Remove `"model"` from `~/.claude/settings.json` to let each alias report its own model name via `--model` flag.
- **Qwen server crash: "cache size limit reached"** — With `--no-kv-offload` and heavy Claude Code usage, the prompt cache fills up and the eviction logic races with new task launches, crashing the server. Fix: `-np 1` (single slot avoids cache pressure from concurrent requests). Also `--cache-reuse 256` is disabled with MTP speculative decoding.
- **Qwopus server memory fitter hang** — The MTP variant GGUF hangs during `fitting params to device memory`. Fix: `-fit off` in the server command.
- **TQ4_1S weight quantization is slower on Blackwell** — 26% slower generation than Q5_K_M on sm_120. The dp4a CUDA kernel cannot compete with Blackwell fp16 tensor cores. No flash-attn support.
- **MoE partial offload kills performance** — Ornith 35B: ngl=99 → 146 t/s, ngl=35 → 13 t/s, ngl=30 → 6 t/s. Must fit all MoE layers on GPU.
- **Flash-attn + sliding window** — Gemma 4 uses hybrid sliding window attention. Flash-attn works but hurts prompt processing (-12%) while helping generation (+22%). llama-bench has a multi-size benchmark bug with FA on sliding window models.
- **Zsh `status` variable is read-only** — Do not use as a local variable name in functions.

## TurboQuant Fork

Fork of llama.cpp by TheTom adding Walsh-Hadamard-rotated KV cache compression and weight quantization types. We use the `feature/turboquant-kv-cache` branch.

### KV Cache Types

| Type | Bits | Compression vs f16 | Use case |
|---|---|---|---|
| `turbo4` | ~4.5 | ~3.5× | conservative V compression |
| `turbo3` | ~3.5 | ~4.6× | **recommended default for V** |
| `turbo2` | ~2.0 | ~8× | aggressive, auto-enables Boundary V protection |

Asymmetric K/V is critical: **keep K at q8_0, compress only V**. Compressing K causes PPL blow-up on many model families.

### KV Cache Savings at Our Context Sizes (turbo3 vs q8_0)

| Model | ctx 131K | ctx 200K |
|---|---|---|
| Ornith 9B | save 1.4 GB | save 2.1 GB |
| Qwen 27B | save 1.8 GB | save 2.8 GB |

### Weight Types (not recommended on Blackwell)

| Type | Notes |
|---|---|
| `TQ4_1S` | ~5.0 bpw, dp4a kernel — 26% slower than Q5_K_M on sm_120 |
| `TQ3_1S` | ~4.0 bpw — not tested |

### Build

```bash
cd ~/llama-cpp-turboquant && git checkout feature/turboquant-kv-cache
export PATH=$HOME/.local/cuda-12.8/bin:$PATH
cmake -B build-turbo -DGGML_CUDA=ON -DGGML_FLASH_ATTN=ON \
  -DCMAKE_CUDA_ARCHITECTURES="120" -DCUDAToolkit_ROOT=$HOME/.local/cuda-12.8 \
  -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-rpath,$HOME/.local/cuda-12.8/lib64" \
  -DCMAKE_EXE_LINKER_FLAGS="-Wl,-rpath,$HOME/.local/cuda-12.8/lib64"
cmake --build build-turbo --config Release -j $(nproc)
```

## APEX Quantization (MoE Models)

MoE-aware mixed-precision quantization by the LocalAI team. Per-layer precision gradient + tensor classification. Runs on **stock** llama.cpp — no custom build needed.

### Tiers for Qwen3.6/Qwopus 35B-A3B (our size: ~35B params, 3B active)

| Tier | ~Size | Expert quant (middle) | Notes |
|---|---|---|---|
| Quality | 23 GB | IQ4_XS | best perplexity |
| Balanced | 25 GB | Q5_K | general purpose |
| Compact | 17 GB | Q3_K | consumer 24 GB |
| Mini | 14 GB | IQ2_S | needs 24 GB or partial offload |
| **Nano** | **11 GB** | **IQ2_XXS** | **fits 16 GB at ngl=99** |

Pre-quantized GGUFs: `https://huggingface.co/mudler` (APEX Quants collection)

**Available for:** Qwen3.6-35B, Qwopus3.6-35B, Ornith-1.0-35B, Gemma-4-26B, Claude Opus distilled variants, and many more.

## Qwopus 35B MoE — Our Setup

Qwopus = Qwen3.6-35B-A3B fine-tuned on Opus reasoning traces (Jackrong). Published independent benchmark: 88.6 Overall, 94.2 Quality, 91.7% Reliability. No SWE-bench scores yet (testing underway).

### Server Config (ccqwopus)

```bash
# Model: Qwopus3.6-35B-A3B-v1-APEX-MTP-I-Nano.gguf (10.9 GiB loaded)
# Build: ~/llama-cpp-turboquant/build-turbo/bin/llama-server
# Port: 8083, FCC proxy: 8100

-m ~/models/qwopus/Qwopus3.6-35B-A3B-v1-APEX-MTP-I-Nano.gguf \
-ngl 99 -t 8 -c 131072 --port 8083 --host 127.0.0.1 \
--temp 0.6 --top-p 0.95 --top-k 20 \
--repeat-penalty 1.1 --dry-multiplier 0.5 --dry-allowed-length 3 --dry-penalty-last-n 4096 \
-ub 4096 -b 4096 --cache-reuse 256 \
--flash-attn on \
-ctk q8_0 -ctv turbo3 \
--reasoning-budget 2048 \
-np 1 -fit off
```

Key: `-fit off` required to bypass memory fitter hang on MTP model variant. `--reasoning-budget 2048` prevents thinking from consuming entire token budget. `--repeat-penalty` + `--dry-multiplier` prevent repetition loops at high context. `--reasoning-preserve` removed (not supported by turboquant). `-np 1` gives single slot full 131K context.

MTP speculative decoding costs ~700 MB VRAM — cannot use with 131K ctx on 16 GB. Bench showed 165 t/s without MTP anyway.

## Complete Benchmarks — RTX 5080 16 GB (Jul 2026)

All benches: turboquant build, turbo3 KV unless noted. FA = flash-attn.

| Model | Size | pp8192 | tg128 | FA | ctx max | SWE-bench | Term-Bench |
|---|---|---|---|---|---|---|---|
| Ornith 9B Q5_K_M | 6.0 GB | 6193 | 122.8 | ✓ | 200K | 69.4% | 43.1% |
| Ornith 9B TQ4_1S | 5.4 GB | 6597 | 92.1 | ✗ | 200K | 69.4% | 43.1% |
| Ornith 35B Mini ngl=99 | 12.5 GB | 4960 | 146.5 | ✓ | ~60K | 75.6% ★ | 64.2% ★ |
| Ornith 35B Mini ngl=35 | 12.5 GB | 2683 | 13.1 | ✓ | ~140K | 75.6% | 64.2% |
| **Qwopus Nano ngl=99** | **10.9 GB** | **6135** | **164.6** | ✓ | **131K** | **~75%** | **~60%** |
| Qwopus Mini ngl=30 | 12.5 GB | 2908 | 31.3 | ✓ | ~145K | ~75% | ~60% |
| Gemma 4 26B Nano FA off | 8.8 GB | 7797 | 138.6 | ✗ | 200K | — | — |
| Gemma 4 26B Nano FA on | 8.8 GB | 6842 | 168.7 | ✓ | 200K | — | — |
| Qwen3.6 35B Mini ngl=30 | 13.3 GB | 2707 | 16.7 | ✓ | ~130K | 73.4% | 52.5% |
| Qwen3.6 27B MTP Q3 turbo3 | 12.0 GB | — | ~17 | ✓ | 131K | ~68% | ~48% |
| Qwen3.6 27B MTP Q3 turbo3 | 12.0 GB | — | ~10 | ✓ | 200K | ~68% | ~48% |

### Winners

| Use case | Model | Why |
|---|---|---|
| **Daily driver** | Ornith 9B Q5 | 123 t/s, 200K, 69.4% SWE, flash-attn |
| **Quality all-round** | Qwopus 35B Nano | 165 t/s, 131K, ~75% SWE, Opus reasoning |
| **Dark horse** | Gemma 4 26B Nano | 8.8 GB, 200K, 7797 pp, no SWE scores yet |
| **Best quality** | Ornith 35B Mini | 75.6% SWE but only 60K ctx — agent-starved |
| **High-ctx dense** | Qwen 27B MTP turbo3 | 200K ctx on single 5080, 10-17 t/s, concise output |
| **Dead** | TQ4_1S, any partial-offload MoE | |

## New Shell Commands

```
cc               # interactive local model picker (ornith / qwen / qwopus)
ccqwopus         # Claude Code with Qwopus 35B Nano (auto-starts server + proxy)
ccstop           # kills all FCC proxies + llama servers

code qwopus      # OpenCode with Qwopus
```

## Qwopus Server Manual Start

```bash
export LD_LIBRARY_PATH=$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH
~/llama-cpp-turboquant/build-turbo/bin/llama-server \
  -m ~/models/qwopus/Qwopus3.6-35B-A3B-v1-APEX-MTP-I-Nano.gguf \
  -ngl 99 -t 8 -c 131072 --port 8083 --host 127.0.0.1 \
  --temp 0.6 --top-p 0.95 --top-k 20 \
  --repeat-penalty 1.1 --dry-multiplier 0.5 --dry-allowed-length 3 --dry-penalty-last-n 4096 \
  -ub 4096 -b 4096 --cache-reuse 256 \
  --flash-attn on \
  -ctk q8_0 -ctv turbo3 \
  --reasoning-budget 2048 \
  -np 1 -fit off

# FCC proxy
PORT=8100 LLAMACPP_BASE_URL="http://127.0.0.1:8083/v1" \
  MODEL="llamacpp/Qwopus3.6-35B-A3B-v1-APEX-MTP-I-Nano.gguf" \
  ENABLE_WEB_SERVER_TOOLS=true FCC_AUTO_INTERCEPT_WEB_TOOLS=true \
  fcc-server > /tmp/fcc-qwopus.log 2>&1 & disown
```

## Multi-GPU Inference

llama.cpp supports splitting models across multiple GPUs via tensor split (`-sm tensor`). The `--fit on` flag (default in recent builds) auto-determines optimal layer distribution and tensor splits.

**For our setup (RTX 5080 16 GB + hypothetical 12 GB GPU = 28 GB):**
- Qwen 27B at 200K would fit (12 GB model + ~15 GB KV cache = 27 GB)
- But **PCIe bandwidth kills speed** for dense models: tested 2x 4090 on Qwen Next showed only +17% speed for 2x hardware
- The slower GPU becomes the bottleneck for any tensor spanning both cards
- For MoE models, multi-GPU is more viable since expert layers can be placed on different GPUs with minimal cross-talk

**Bottom line:** turbo3 KV cache compression on a single 5080 is better than adding a second GPU for our use case. 200K context already fits with turbo3.
