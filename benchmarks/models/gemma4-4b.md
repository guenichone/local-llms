# Gemma 4 E4B

## Model Info
- **Family:** gemma4 — 4B dense, hybrid sliding window attention
- **Quant:** Q4_K_M (3 GB)
- **Build:** vanilla llama.cpp
- **Context max:** 32K
- **Notes:** Only ~3GB VRAM. Fits alongside other models (no conflict for VRAM). Fast, no reasoning overhead. Good for Hermes quick tasks.

## References
- [HF] https://huggingface.co/google/gemma-4
- Needs `HF_TOKEN` for gated repo access.
- Uses `--chat-template gemma` flag.

## Benchmark Runs

<!-- Auto-populated by run_full_benchmark.py -->
