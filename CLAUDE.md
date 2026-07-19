# Local LLMs Setup (WSL2 + RTX 5080)

## Quick Reference

```bash
# ── Claude Code ──
claude-or                          # Opus 4.8 via OpenRouter ($)
claude-or-sonnet                   # Sonnet 5 via OpenRouter
  ccornith                        # Ornith Q5 (local, free, ~30s delay)
  ccqwen                           # Qwen3.6-27B MTP (local)

# ── OpenCode ──
code ds                            # DeepSeek V4 Flash
code ornith                        # Ornith Q5 (local llama.cpp)
code local                         # Qwen3.6-27B MTP (local)

# ── Ornith server ──
ccornith                           # auto-starts server + proxy
ccqwen                             # auto-starts Qwen server + proxy
llama-server ...                   # or manual: see Server Commands below

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

#### Qwen3.6-27B MTP (port 8080)

```bash
export LD_LIBRARY_PATH=$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH
llama-server \
  -m ~/models/qwen3.6-27b-mtp-Q3_K_S.gguf \
  -ngl 99 -t 8 -c 200000 --no-kv-offload --port 8080 --host 127.0.0.1 \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  -np 2 --cache-reuse 256
```

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

## Performance (RTX 5080)

### llama-bench — July 2026 (CUDA 12.8, vanilla build, fully GPU-resident)

| Model | Threads | Flash-Attn | pp512 t/s | tg128 t/s | Notes |
|---|---|---|---|---|---|
| **Ornith 9B Q5_K_M** | **6** | **on** | **6,044** | **131.4** | Best: vanilla build, t=6 optimal |
| Ornith 9B Q5_K_M | 8 | on | 5,742 | 123.5 | tg drops at higher threads |
| Ornith 9B Q5_K_M | 6 | off | 5,243 | 125.2 | FA gives +15% pp |
| Qwen 27B Q3_K_S | 8 | on | 1,692 | 47.4 | Best pp at t=8 |
| Qwen 27B Q3_K_S | 4 | on | 1,611 | 48.3 | Best tg at t=4 |
| Qwen 27B Q3_K_S + MTP | 8 | on | — | **~96** | MTP ≈2x decode (llama-bench can't test) |

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
- **Qwen 27B with 200K context requires `--no-kv-offload`** — KV cache (~10 GB at 200K) must stay in system RAM (DDR5 7200 bandwidth is sufficient). Without it, max usable context is ~65K on 16 GB VRAM.
- **FCC proxy model display** — Remove `"model"` from `~/.claude/settings.json` to let each alias report its own model name via `--model` flag.
- **Qwen server crash: "cache size limit reached"** — With `--no-kv-offload` and heavy Claude Code usage, the prompt cache fills up and the eviction logic races with new task launches, crashing the server (`operator(): cleaning up before exit...`). Fix: add `--cache-reuse 256` (enables KV cache prefix reuse across agent requests) and `-np 2` (reduces slots from 4 to 2, cutting cache pressure). Also confirmed: CUDA 13.3 driver + CUDA 12.8 user-mode libs is the optimal Blackwell config — the 13.3 kernel-mode driver is fully backward compatible with 12.8-compiled binaries; only CUDA 13.3 *libs* trigger the sm_120 MMQ bugs.
