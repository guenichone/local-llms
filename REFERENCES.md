# References & Learnings Index

Part of the [local-llms](https://github.com/guenichone/local-llms) setup repo.
Cross-referenced with [CLAUDE.md](./CLAUDE.md).

Key: 🎥 video &nbsp; 📄 paper &nbsp; 📝 blog &nbsp; 🔧 PR/issue &nbsp; 📦 model &nbsp; 🍴 fork

---

## Videos

### Can a 3.5GB model replace my 35B daily driver? (Bonsai 27B)
- 🎥 [YouTube](https://www.youtube.com/watch?v=rBLWDJrXCp0) — Codacus — 2026-07-19
- **Topics:** Bonsai, 1-bit weights, ternary, MoE vs dense, quantization, memory footprint
- **Key claims:**
  - Bonsai 27B: true 1-bit weights trained as -1/+1 (not post-training quantization), like BitNet/QAT taken to 1-bit
  - Binary Q1_0 (3.5 GB) / Ternary Q2_0 (7 GB), compressed from Qwen 27B dense
  - Ternary matches 35B MoE on design quality and server repair; binary is a tier below
  - Gemma 12B fails long complex tasks — decision-looping is model-level, not config fixable
  - MoE shrinks the *math* (3B active params), quantization shrinks the *file* — different mechanisms
  - Speed on RTX 3060: MoE 47.9, Bonsai Q1 34.7, Bonsai Q2 21.6 t/s
  - **Total footprint** is the real metric: MoE 21 GB (VRAM+RAM leak), ternary 8.8 GB, binary 5.3 GB
  - Apple Silicon / unified memory: MoE doesn't fit (no second tier). Bonsai ternary is the pick (Metal merged)
  - **Future:** ternary MoE = stacked tricks — 250B class at ~20 GB download
- **Relevance:** Bonsai could replace Ornith 9B Q5 as daily driver (7 GB ternary ≈ 35B MoE quality). Needs CUDA PR #25707 for sm_120.
- **Related:** `llama.cpp` CUDA Q2_0 PR #25707, Metal Q2_0 #25419, `huggingface.co/prism-ml`

### I Asked Claude Fable 5 to Improve llama.cpp
- 🎥 [YouTube](https://www.youtube.com/watch?v=VytSYCDhWQ0) — TheCodacus — 2026-07
- **Topics:** Fable 5, CUDA optimization, mmap pinning, expert prefetch, MoE
- **Key claims:**
  - 4 optimizations proposed: mmap pinning, expert prefetch, adaptive spec controller, CPU+GPU split
  - Mmap pinning (`cudaHostRegister`): +135% prompt processing when weights in RAM, 0% when GPU-resident
  - Expert prefetch: upload MoE expert tensors via background CUDA stream
  - Output verified token-identical to vanilla llama.cpp
- **Relevance:** Our fable5-optimizations fork applies the 2 winning optimizations. Used for partial-offload MoE.
- **Related:** `github.com/thecodacus/llama.cpp` (branches: fable5/host-register, fable5/prefetch-experts), `github.com/guenichone/llama.cpp:fable5-optimizations`

---

## Papers & Technical Writeups

### Ornith 1.0 Technical Write-up
- 📄 [deep-reinforce.com](https://deep-reinforce.com/ornith_1_0.html) — DeepReinforce — 2026
- **Topics:** Ornith, RLHF, self-scaffolding, Qwen post-training
- **Key claims:**
  - Self-scaffolding: model jointly produces solution + task-specific scaffolds during RL
  - Three defenses against reward hacking: fixed outer trust boundary, deterministic monitor, frozen LLM judge
  - Ornith 397B: Terminal-Bench 77.5, SWE-Bench Verified 82.4 (edges Opus 4.7, trails Opus 4.8)
  - Ornith 35B MoE: Terminal-Bench 64.2, SWE-Bench 75.6 — beats Qwen 3.5-397B
  - Ornith 9B: Terminal-Bench 43.1, SWE-Bench 69.4
- **Relevance:** Our primary coding agent (Ornith 9B Q5_K_M). 35B MoE variant is the best local option for 24 GB GPUs.
- **Related:** `huggingface.co/collections/deepreinforce-ai/ornith-10`

### BitNet: Scaling 1-bit Transformers
- 📄 [arXiv:2310.11453](https://arxiv.org/abs/2310.11453) — Microsoft Research — 2023
- **Topics:** 1-bit weights, ternary, training efficiency, BitLinear
- **Key claims:** Weights constrained to {-1, 0, +1} during training (BitLinear layer), competitive with full-precision at scale
- **Relevance:** Theoretical foundation behind Bonsai 27B. Future models will likely use this approach for dense compression.

---

## Blog Posts & Articles

### How to Run Ornith 1.0 Locally (2026)
- 📝 [codersera.com](https://codersera.com/blog/how-to-run-ornith-1-0-locally-2026/) — Codersera — 2026
- **Topics:** Ornith, Ollama, LM Studio, vLLM, agent wiring, tool parsers, quant picks
- **Relevance:** Our source for Ornith quant comparison and agent integration patterns.

### How to Run Qwen 3.6 Locally (2026)
- 📝 [codersera.com](https://codersera.com/blog/how-to-run-qwen-3-6-locally-2026/) — 2026
- **Relevance:** Reference for our Qwen 27B MTP and Qwen 35B MoE setups.

### Open-Source LLMs Landscape 2026
- 📝 [codersera.com](https://codersera.com/blog/open-source-llms-landscape-2026/) — 2026

### Best Free Local LLM Tools 2026
- 📝 [codersera.com](https://codersera.com/blog/best-free-local-llm-tools-2026/) — 2026

---

## GitHub PRs & Issues

### llama.cpp — Blackwell sm_120 MMQ kernel bug
- 🔧 [llama.cpp#18049](https://github.com/ggml-org/llama.cpp/discussions/18049) — 2025-12
- **Topics:** multi-GPU, tensor split, auto-fit, memory automation, MoE optimization
- **Key claims:** Auto-fit (`--fit on`) does virtual test allocations across GPUs, iterative memory reduction. 2x RTX 4090 on Qwen 3 Next q8_0: only +17% speed for 2x hardware. VRAM utilization ~88%.
- **Relevance:** Multi-GPU possible but PCIe penalty kills dense model performance. turbo3 KV compression better than 2nd GPU.

- 🔧 [llama.cpp#24399](https://github.com/ggml-org/llama.cpp/issues/24399) — 2026
- **Topics:** CUDA 13.1+, Blackwell, MMQ, sm_120, build
- **Key claims:**
  - `mul_mat_q<Q8_0>` — out-of-range shared store (crash after ~hundreds of gens)
  - `flash_attn_ext_f16` — flash attention kernel crash
  - cuBLASLt TF32 split-k — barrier mismatch
- **Relevance:** **Critical bug for RTX 5080 (Blackwell).** Fix: build llama.cpp with CUDA 12.8 (not 13.1+). Our whole inference stack depends on this workaround.
- **Related:** CUDA 12.8 build instructions in CLAUDE.md

### llama.cpp — CUDA Q2_0 support (Bonsai)
- 🔧 [llama.cpp#25707](https://github.com/ggml-org/llama.cpp/pull/25707) — open — 2026-07
- **Topics:** Bonsai, Q2_0, CUDA kernel, 1-bit weights
- **Relevance:** Required to run Bonsai 27B on NVIDIA GPUs. Currently an open PR — need to build from this branch for sm_120.

### llama.cpp — Metal Q2_0 support (Bonsai)
- 🔧 [llama.cpp#25419](https://github.com/ggml-org/llama.cpp/pull/25419) — merged — 2026
- **Topics:** Bonsai, Q2_0, Metal, Apple Silicon
- **Relevance:** Already merged — Mac users can run Bonsai from mainline.

### llama.cpp — MTP Issue (speculative decoding)
- 🔧 [llama.cpp#24399](https://github.com/ggml-org/llama.cpp/issues/24399) — 2026
- **Topics:** MTP, speculative decoding, Blackwell
- **Relevance:** MTP speculative decoding gives ~2x generation speed on Qwen 27B (48 → 96 t/s). Disabled on our Qwopus build (MTP costs 1.6 GB VRAM, conflicts with 131K ctx).

---

## Models & HuggingFace Collections

### Ornith 1.0 Collection
- 📦 [huggingface.co/collections/deepreinforce-ai/ornith-10](https://huggingface.co/collections/deepreinforce-ai/ornith-10) — DeepReinforce AI
- Variants: 9B Dense, 35B MoE, 397B MoE
- **Our pick:** `Ornith-1.0-9B-Q5_K_M.gguf` (6.1 GB, 123 t/s on 5080)
- **Related:** `bartowski/deepreinforce-ai_Ornith-1.0-9B-GGUF`

### Ornith 9B GGUF (bartowski)
- 📦 [huggingface.co/bartowski/deepreinforce-ai_Ornith-1.0-9B-GGUF](https://huggingface.co/bartowski/deepreinforce-ai_Ornith-1.0-9B-GGUF) — bartowski
- Source for our Q4, Q5, Q6 GGUF files

### Ornith NVFP4 MTP GGUF
- 📦 [huggingface.co/s-batman/Ornith-1.0-9B-NVFP4-MTP-GGUF](https://huggingface.co/s-batman/Ornith-1.0-9B-NVFP4-MTP-GGUF) — s-batman
- Native Blackwell format — **tested, worse than Q5_K_M** (3/11 tasks empty, slower kernels)

### Bonsai 27B (PrismML)
- 📦 [huggingface.co/prism-ml](https://huggingface.co/prism-ml) — PrismML — 2026-07
- Binary Q1_0 (3.5 GB) / Ternary Q2_0 (7 GB) — compressed from Qwen 27B dense
- True 1-bit weights trained from day one (not post-training quantization)
- **Status:** Not yet tested on our rig. Needs CUDA PR #25707 build.

### Qwopus 35B MoE (Jackrong)
- 📦 HuggingFace — Jackrong — 2026-07
- Qwen3.6-35B-A3B fine-tuned on Opus reasoning traces
- **Our pick:** `Qwopus3.6-35B-A3B-v1-APEX-MTP-I-Nano.gguf` (10.9 GB, 165 t/s, 131K ctx)
- **Related:** `mudler` (APEX Quants collection)

### APEX Quantized Models (MoE-aware)
- 📦 [huggingface.co/mudler](https://huggingface.co/mudler) — LocalAI team (mudler)
- MoE-aware mixed-precision quantization. Per-layer precision gradient + tensor classification.
- Runs on **stock** llama.cpp — no custom build needed
- Available: Qwen3.6-35B, Qwopus3.6-35B, Ornith-1.0-35B, Gemma-4-26B, Claude Opus distilled, etc.

### Qwen 3.6 35B-A3B GGUF
- 📦 [huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF) — Unsloth
- 35B params, 3B active MoE. Q4_K_M ~21 GB total footprint.
- **Relevance:** Reference MoE model from Codacus Bonsai video. Our Qwopus is derived from this.

---

## Forks & Builds

### llama.cpp — Fable 5 Optimizations (our fork)
- 🍴 [github.com/guenichone/llama.cpp:fable5-optimizations](https://github.com/guenichone/llama.cpp/tree/fable5-optimizations)
- Applies 2 optimizations: mmap pinning + expert prefetch
- Build: `cmake -DGGML_CUDA=ON -DGGML_FLASH_ATTN=ON -DCMAKE_CUDA_ARCHITECTURES="120" -DCUDAToolkit_ROOT=$HOME/.local/cuda-12.8`
- Must export `GGML_CUDA_REGISTER_HOST=1` or decode collapses to <2 t/s

### llama.cpp — Fable 5 (original)
- 🍴 [github.com/thecodacus/llama.cpp](https://github.com/thecodacus/llama.cpp) — TheCodacus
- Branches: `fable5/host-register`, `fable5/prefetch-experts`

### llama-cpp-turboquant
- 🍴 [github.com/TheTom/llama-cpp-turboquant](https://github.com/TheTom/llama-cpp-turboquant) (branch: `feature/turboquant-kv-cache`)
- Walsh-Hadamard-rotated KV cache compression (turbo2/3/4 types) + TQ weight quants
- **Our picks:** `-ctk q8_0 -ctv turbo3` (asymmetric: keep K at q8_0, compress V only)
- **Savings:** turbo3 vs q8_0 saves 1.4 GB at 131K ctx (Ornith 9B), 2.8 GB at 200K (Qwen 27B)
- **Weight types:** TQ4_1S, TQ3_1S — NOT recommended on Blackwell (26% slower than Q5_K_M on sm_120)
- Used for our Qwopus build

---

## Tools & Frameworks

### OpenCode
- 📝 [opencode.ai](https://opencode.ai) — primary agent framework
- Configured in `opencode.json` with local providers (ornith, local) and cloud (openrouter, deepseek)

### Hermes Agent
- 📝 [github.com/NousResearch/Hermes-Agent](https://github.com/NousResearch/Hermes-Agent) — NousResearch
- Tested harness for Ornith. Profiles configured via `~/.hermes/profiles/`
- **Our profiles:** ornith, qwopus, gemma4, deepseek-v4-pro

### free-claude-code (fcc)
- 📝 [github.com/Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code)
- Anthropic protocol → OpenAI Chat Completions proxy for Claude Code
- Installed via uv, Python 3.14.4
- Used for: ccornith, ccqwen, ccqwopus

### llama.cpp
- 📝 [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) — primary inference engine
- Build: CUDA 12.8, sm_120, flash-attn on
- **Critical:** Must build with CUDA 12.8 (not 13.1+) due to Blackwell MMQ bug

---

## GitHub Repositories

### Our Repos
| Repo | Description |
|---|---|
| [guenichone/local-llms](https://github.com/guenichone/local-llms) | This repo — local LLM setup on WSL2 + RTX 5080 |
| [guenichone/llama.cpp](https://github.com/guenichone/llama.cpp) (branch: `fable5-optimizations`) | Fable 5 patches: mmap pinning + expert prefetch for Blackwell |

### Upstream Inference
| Repo | Description |
|---|---|
| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | Primary inference engine. Build with CUDA 12.8 for Blackwell. |
| [TheTom/llama-cpp-turboquant](https://github.com/TheTom/llama-cpp-turboquant) (branch: `feature/turboquant-kv-cache`) | Walsh-Hadamard KV cache compression (turbo2/3/4) + TQ weight quants |
| [thecodacus/llama.cpp](https://github.com/thecodacus/llama.cpp) (branches: `fable5/host-register`, `fable5/prefetch-experts`) | Claude Fable 5 CUDA optimizations experiment |

### Model Producers
| Repo | Description |
|---|---|
| [deepreinforce-ai](https://huggingface.co/collections/deepreinforce-ai/ornith-10) | Ornith 1.0 (9B / 35B MoE / 397B MoE) |
| [prism-ml](https://huggingface.co/prism-ml) | Bonsai 27B — 1-bit weights, binary/ternary builds |
| [Jackrong](https://huggingface.co/) (Qwopus) | Qwopus 35B MoE — Qwen distilled on Opus reasoning traces |
| [mudler](https://huggingface.co/mudler) (APEX Quants) | MoE-aware mixed-precision GGUF quants for Qwen/Qwopus/Gemma/etc. |
| [bartowski](https://huggingface.co/bartowski) | GGUF quantization hub (Ornith 9B Q4/Q5/Q6) |
| [s-batman](https://huggingface.co/s-batman) | Ornith NVFP4-MTP (Blackwell native, worse than Q5_K_M) |
| [unsloth](https://huggingface.co/unsloth) | Qwen 3.6 35B-A3B GGUF |

### Agent Frameworks & Tools
| Repo | Description |
|---|---|
| [opencode](https://github.com/anomalyco/opencode) | CLI agent framework — our primary tool |
| [NousResearch/Hermes-Agent](https://github.com/NousResearch/Hermes-Agent) | Agent harness with memory, compression, multi-platform support |
| [Alishahryar1/free-claude-code](https://github.com/Alishahryar1/free-claude-code) | Anthropic → OpenAI proxy for Claude Code with local models |

---

## Quick Topic Index

| Topic | Sources |
|---|---|
| **Quantization** (Q4/Q5/Q6/NVFP4) | Ornith blog, our benchmarks (CLAUDE.md) |
| **1-bit/ternary weights** (Bonsai) | Codacus video, BitNet paper, PR #25707 |
| **MoE vs dense** (A3B vs 27B) | Codacus video, Qwopus setup |
| **Blackwell CUDA bugs** (sm_120) | Issue #24399, CUDA 12.8 build |
| **Flash Attention** +sliding window | Our benchmarks, Gemma 4 FA tradeoff |
| **KV cache compression** (turboquant) | TurboQuant fork, turbo3 vs q8_0 |
| **MTP speculative decoding** | Issue #24399, Qwen 27B MTP setup |
| **Mmap pinning** + expert prefetch | Fable 5 video, our fork |
| **APEX MoE quantization** | mudler HF collection, Qwopus Nano |
| **Agent wiring** (Hermes, OpenCode, fcc) | Codersera guides, our providers.zsh |
| **Total memory footprint** | Codacus Bonsai video, our 16 GB VRAM constraint |
| **Model selection per hardware** | Codacus verdict, our benchmarks table |
| **Self-scaffolding** (Ornith) | DeepReinforce write-up |
| **Ornith benchmarks** (SWE, Terminal) | DeepReinforce, our 11-task quant comparison |
| **Gemma 4 sliding window attention** | Our FA benchmarks, Gemma model cards |
