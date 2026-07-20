# Qwopus 35B Nano

## Model Info
- **Family:** qwopus — Qwen3.6-35B-A3B fine-tuned on Opus reasoning traces by Jackrong
- **Architecture:** 35B MoE (3B active), 256 experts, MTP heads
- **Quant:** APEX Nano (IQ2_XXS, ~11 GB), fits 16GB at ngl=99
- **Build:** turboquant (turbo3 KV cache)
- **Speed:** pp8192=6135 t/s, tg128=165 t/s
- **Context max:** 131K
- **External scores:** Published independent benchmark: 88.6 Overall, 94.2 Quality, 91.7% Reliability. No SWE-bench scores yet (testing underway).
- **Known issues:** `-fit off` required (MTP variant GGUF hangs on memory fitter). `--reasoning-budget 2048` to prevent thinking from consuming entire budget. Repeat penalty + dry sampler needed at high context.

## References
- [HF] https://huggingface.co/mudler (APEX Quants collection)
- [Repo] https://github.com/TheTom/llama-cpp-turboquant (turboquant fork)

## Benchmark Runs

<!-- Auto-populated by run_full_benchmark.py -->
