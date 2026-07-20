# Ornith-1.0-9B

## Benchmark Run — 2026-07-20T16:56:13
- **Quant:** Q5_K_M (6.1 GB)
- **Build:** vanilla
- **Speed:**
  - ngl0_t6: pp=850 t/s, tg=6.7 t/s
  - ngl99_t4_fa_on: pp=5782 t/s, tg=130.0 t/s
  - ngl99_t6_fa_off: pp=5833 t/s, tg=128.8 t/s
  - ngl99_t6_fa_on: pp=5852 t/s, tg=130.3 t/s
  - ngl99_t6_fa_on_kv_q4_0: pp=5743 t/s, tg=122.0 t/s
  - ngl99_t6_fa_on_kv_q8_0: pp=5761 t/s, tg=125.8 t/s
  - ngl99_t8_fa_on: pp=5792 t/s, tg=130.1 t/s
- **VRAM:** delta=12202 MB, model=6246 MB, kv cache=5956 MB @ctx=200000
- **Result file:** `benchmarks/results_ornith-1.0-9b_Q5_K_M_20260720*.json`
- **References:**
  - [HF] https://huggingface.co/collections/deepreinforce-ai/ornith-10
  - [HF] https://huggingface.co/bartowski/deepreinforce-ai_Ornith-1.0-9B-GGUF
  - [HF] https://huggingface.co/s-batman/Ornith-1.0-9b-NVFP4-MTP-GGUF
  - [Article] https://deep-reinforce.com/ornith_1_0.html
  - [Article] https://codersera.com/blog/how-to-run-ornith-1-0-locally-2026/

## Model Info
- **Family:** qwen35 — post-trained on Qwen 3.5
- **Architecture:** 9B dense, 33 layers, GQA (32 q_heads, 8 kv_heads), 128 head_dim, 256K theoretical ctx
- **Key innovation:** Self-scaffolding — model jointly produces solution rollouts + task-specific scaffolds during RL
- **Tool format:** Qwen-style XML (`qwen3_xml`) + `<think>` reasoning blocks
- **External scores:** SWE-bench Verified 69.4%, Terminal-Bench 43.1%
- **Best quant for 16GB:** Q5_K_M (6.1 GB, ~130 t/s, 200K ctx)
- **Quants tested:** Q4_K_M (5.3GB), Q5_K_M (6.1GB), Q6_K (7.2GB, not recommended), NVFP4-MTP (5.1GB, not recommended)
