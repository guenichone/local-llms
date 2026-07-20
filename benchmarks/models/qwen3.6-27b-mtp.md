# Qwen3.6-27B MTP

## Model Info
- **Family:** qwen36 — 27B dense, MTP speculative decoding heads
- **Quant:** Q3_K_S (12 GB)
- **Build:** turboquant (turbo3 KV cache)
- **Speed:** pp512=1692 t/s, tg128=47 t/s (no MTP), ~60 t/s (MTP at 55K ctx)
- **Context max:** 200K (with turbo3 KV)
- **Context vs speed:** 55K=60 t/s, 131K=17 t/s, 200K=10 t/s
- **Known issues:** MTP disables `--cache-reuse`. Only one slot (`-np 1`) to prevent cache eviction crashes. `--no-kv-offload` causes 3.2x slowdown. `-t 4` optimal for gen speed.
- **Notes:** Concise output style (no reasoning blocks). Good for high-context agent workloads.

## References
- [Article] https://codersera.com/blog/how-to-run-qwen-3-6-locally-2026/
- [Repo] https://github.com/TheTom/llama-cpp-turboquant (turboquant fork)

## Benchmark Runs

<!-- Auto-populated by run_full_benchmark.py -->
