# Local LLMs — RTX 5080 WSL2 Setup

[![Platform: Linux](https://img.shields.io/badge/platform-WSL2%20%7C%20Ubuntu%2024.04-orange.svg)](#hardware)
[![GPU: RTX 5080](https://img.shields.io/badge/GPU-RTX%205080-76B900.svg)](#hardware)
[![CUDA: 12.8](https://img.shields.io/badge/CUDA-12.8-green.svg)](#cuda-build)

Curated configuration and benchmarks for running local LLMs on a consumer RTX 5080 GPU (16 GB VRAM, Blackwell sm_120) under WSL2. Covers CUDA build workarounds, optimal llama.cpp server flags, agent wiring, and model quantization benchmarks.

## Quick Reference

```bash
claude-or                          # Claude Code via OpenRouter (Opus 4.8)
ccornith                           # Claude Code via local Ornith Q5_K_M
ccqwen                             # Claude Code via local Qwen3.6-27B MTP
code                               # OpenCode model picker
code ornith                        # OpenCode via local Ornith
code local                         # OpenCode via local Qwen MTP
yt-transcript <url>                # YouTube transcript + metadata
```

## Hardware

| Component | Spec |
|-----------|------|
| GPU | NVIDIA GeForce RTX 5080 (16 GB VRAM, Blackwell SM 12.0) |
| CPU | AMD Ryzen 7 9800X3D |
| RAM | 32 GB (15 GB WSL2 allocation) |
| OS | WSL2 — Ubuntu 24.04 LTS |
| CUDA | 12.8.61 (llama.cpp builds) + 13.3 (system driver) |

## CUDA Build

### Blackwell MMQ Bug

CUDA 13.1+ has a known MMQ kernel bug on sm_120 — `mul_mat_q` produces out-of-range shared-memory stores, causing crashes and silent cuBLAS fallback (5-6x slower prompt). **Fix:** build with CUDA 12.8.

```bash
export PATH=$HOME/.local/cuda-12.8/bin:$PATH
export LD_LIBRARY_PATH=$HOME/.local/cuda-12.8/lib64:$LD_LIBRARY_PATH

cmake -B build \
  -DGGML_CUDA=ON -DGGML_FLASH_ATTN=ON \
  -DGGML_CUDA_FORCE_CUBLAS=OFF \
  -DCMAKE_CUDA_ARCHITECTURES="120" \
  -DCUDAToolkit_ROOT=$HOME/.local/cuda-12.8
cmake --build build --config Release -j $(nproc)
```

## Models

| Model | Params | Quant | Size | Notes |
|-------|--------|-------|------|-------|
| Ornith-1.0-9B | 9B | **Q5_K_M** | 6.1 GB | Primary coding agent |
| Ornith-1.0-9B | 9B | Q4_K_M | 5.3 GB | Fallback, lower quality |
| Qwen3.6-27B MTP | 27B | Q3_K_S | 12 GB | MTP speculative decoding (~2x speed) |
| Qwen3.5-27B | 27B | Q4_K_M | 17 GB | Only fits with partial offload |
| Gemma 4 E4B | 4B | Q4_K_M | 3 GB | Fast, CPU-friendly |

## Server Commands

### Ornith 9B Q5_K_M (port 8082) — primary agent

```bash
llama-server \
  -m ~/models/ornith-1.0-9b/ornith-1.0-9b-Q5_K_M.gguf \
  -ngl 99 -t 6 -c 200000 --port 8082 --host 127.0.0.1 \
  --temp 0.6 --top-p 0.95 --top-k 20 \
  -ub 4096 -b 4096 --cache-reuse 256 \
  --flash-attn on --reasoning-preserve \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  -np 6 --kv-unified
```

### Qwen3.6-27B MTP (port 8080) — speculative decoding

```bash
llama-server \
  -m ~/models/qwen3.6-27b-mtp-Q3_K_S.gguf \
  -ngl 99 -t 8 -c 200000 --port 8080 --host 127.0.0.1 \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  --flash-attn on --no-kv-offload \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  -np 1
```

## Benchmarks

11-task coding benchmark (generation, debugging, refactoring, testing, security). Non-streaming, `max_tokens=4096`, `temp=0.6`.

### Quantization Comparison (RTX 5080, CUDA 12.8)

| Quant | Prompt t/s | Gen t/s | TTFT | Bug-finding |
|-------|-----------|---------|------|-------------|
| **Q5_K_M** | **1,585** | **117** | **29s** | **Found all** |
| Q4_K_M | 725 | 123 | 23s | Missed bugs |
| Q6_K | 970 | 48 | 57s | Good, 2.4x slower |
| NVFP4-MTP | 751 | 76 | 49s | 3/11 tasks empty |

### llama-bench (fully GPU-resident, flash-attn on)

| Model | Threads | pp512 t/s | tg128 t/s |
|-------|---------|-----------|-----------|
| Ornith 9B Q5_K_M | 6 | 6,044 | 131.4 |
| Qwen 27B Q3_K_S | 8 | 1,692 | 47.4 |
| Qwen 27B Q3_K_S + MTP | 8 | — | ~96 |

### Fable 5 Optimizations (patched build)

| Scenario | Vanilla | Patched | Gain |
|----------|---------|---------|------|
| All-CPU prompt | 751 t/s | 1,771 t/s | +135% |
| Partial offload prompt | 2,077 t/s | 3,257 t/s | +57% |
| Fully GPU-resident | 5,935 t/s | 5,812 t/s | -2% |

## Agent Wiring

Shell aliases in `~/.zshrc.d/providers.zsh`. API keys in `.env`.

### Claude Code

| Alias | Backend | Model |
|-------|---------|-------|
| `claude-or` | OpenRouter proxy (:8099) | Claude Opus 4.8 / Sonnet 5 / Haiku 4.5 |
| `ccornith` | free-claude-code (:8097) → llama-server (:8082) | Ornith 9B Q5_K_M |
| `ccqwen` | free-claude-code (:8098) → llama-server (:8080) | Qwen 3.6 27B MTP |

### OpenCode

```bash
code ds         # DeepSeek V4 Flash
code glm        # GLM 5.2
code qwen       # Qwen 3.6 27B
code ornith     # Ornith Q5 (local)
code local      # Qwen 27B MTP (local)
```

## Ornith 1.0 Notes

- **Architecture:** Post-trained on Qwen 3.5. Self-scaffolding RL — model authors its own task-specific scaffolds during training.
- **Reasoning overhead:** ~1000+ tokens in `<think>` before visible output. Always set `max_tokens >= 4096`.
- **Tool calling:** Qwen XML format. Under llama.cpp use `--reasoning-preserve`.
- **Context:** 256K theoretical. 131K works on 16 GB with KV cache quant.

## Environment Variables

```bash
OPENROUTER_API_KEY=sk-or-...     # OpenRouter (claude-or, code)
DEEPSEEK_API_KEY=sk-...          # Optional — direct DeepSeek
HF_TOKEN=hf_...                  # Gated HuggingFace models (Gemma)
```

## Known Issues

- **One model at a time in VRAM** — Qwen 27B (12 GB) + Ornith 9B (6 GB) = 18 GB > 16 GB. `ccornith`/`ccqwen` auto-kill the other.
- **Ornith TTFT ~29s** — reasoning block overhead, normal for the model class.
- **Fable5 patched build needs `GGML_CUDA_REGISTER_HOST=1`** or decode collapses to <2 t/s.
- **Qwen 200K context needs `--no-kv-offload`** — KV cache ~10 GB at max context.
