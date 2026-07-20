---
name: benchmark-model
description: |
  Run comprehensive benchmarks on local llama.cpp models: speed (llama-bench),
  memory (VRAM/RAM footprint, KV cache), and coding quality (11-task benchmark).
  Use when the user asks to benchmark a model, compare quants, measure memory
  usage, run speed tests, or update CLAUDE.md benchmark tables with new results.
  Also use when adding a new model to the benchmark system.
---

# Model Benchmarking

## Overview

Benchmark local llama.cpp models across three dimensions: speed, memory, and coding quality. Results are normalized into a unified `master_results.json` for cross-model comparison and auto-update CLAUDE.md tables.

## Quick Reference

```bash
# Full speed + memory benchmark (default, ~2 min)
python3 benchmarks/run_full_benchmark.py --model ornith-1.0-9b --quant Q5_K_M

# Speed only (~1 min)
python3 benchmarks/run_full_benchmark.py --model ornith-1.0-9b --quant Q5_K_M --speed-only

# With coding benchmark (~5-7 min extra)
python3 benchmarks/run_full_benchmark.py --model ornith-1.0-9b --quant Q5_K_M --coding

# All phases
python3 benchmarks/run_full_benchmark.py --model qwopus-35b-nano --quant Nano --all

# List available models/quants
python3 benchmarks/run_full_benchmark.py --list
```

## What Gets Measured

### Speed (llama-bench)
- `pp512` + `tg128` at `-ngl 99` (full GPU), `-ngl <partial>` (mixed), `-ngl 0` (CPU)
- Flash-attn on/off comparison
- Thread sweep: 4, 6, 8
- Cache type variants: f16, q8_0, q4_0 (vanilla) / turbo3 (turboquant)
- MTP speculative decoding variants for supported models

### Memory (nvidia-smi + /proc/meminfo)
- Baseline VRAM/RAM (idle system)
- Model VRAM (after server start, before KV allocation)
- KV cache VRAM at multiple context sizes
- Theoretical KV cache from model architecture
- System RAM delta

### Coding Quality (11-task coding benchmark)
- 11 tasks: code generation (3), debugging (2), refactoring (2), testing (2), security (1), optimization (1)
- Metrics: TTFT, gen t/s, prompt t/s, token counts, empty output rate
- Requires `--coding` flag (opt-in, ~5-7 min)

## Output Files

| File | Location | Content |
|---|---|---|
| Per-run JSON | `benchmarks/results_{model}_{quant}_{ts}.json` | Detailed raw results |
| Master results | `benchmarks/master_results.json` | Normalized cross-model comparison |
| Per-model knowledge | `benchmarks/models/<model>.md` | All findings, links, references for one model |
| Coding outputs | `benchmarks/outputs/` | Raw model responses per task |

## Model Registry

Models are configured in `run_full_benchmark.py`'s `MODEL_REGISTRY` dict. To add a new model:

1. Add entry to `MODEL_REGISTRY` with: name, family, quants, build path, port, server args, external scores
2. Run `--speed-only` first to verify it works
3. Then `--all` for full benchmark
4. Results auto-flow to `master_results.json` and `benchmarks/models/<model>.md`

### Registry structure:
```python
MODEL_REGISTRY = {
    "model-key": {
        "name": "Display Name",
        "family": "qwen35|gemma|qwopus",
        "quants": {"Q5_K_M": {"file": "model-Q5_K_M.gguf", "size_gb": 6.1}, ...},
        "build": "vanilla",               # or "turboquant"
        "llama_build_path": "~/llama.cpp/build/bin",  # for llama-bench
        "turboquant_build_path": "~/llama-cpp-turboquant/build-turbo/bin",  # optional
        "port": 8082,
        "server_args": {"-t": 6, "--flash-attn": "on", ...},
        "external": {"swe_bench_verified": 69.4, "terminal_bench": 43.1},
    }
}
```

## Updating CLAUDE.md

After running benchmarks:

1. The script shows a computed diff for the `## Complete Benchmarks` table
2. Review the diff and confirm to auto-apply
3. If declined, results are still saved to `master_results.json` and per-model .md
4. Per-model .md files serve as the source of truth — CLAUDE.md tables are a "view" derived from master_results.json

### Manual update path:
```bash
# Regenerate CLAUDE.md table from master_results.json
python3 benchmarks/run_full_benchmark.py --diff-claude
```

## Adding External Scores

When new SWE-bench or Terminal-bench scores are published:

1. Update the `"external"` dict in `MODEL_REGISTRY` in `run_full_benchmark.py`
2. Update `benchmarks/master_results.json` for any existing entries
3. Regenerate CLAUDE.md table: `--diff-claude`

## Workflow for New Model Testing

```
1. Add to MODEL_REGISTRY in run_full_benchmark.py
2. --speed-only to verify server starts and llama-bench works
3. Fix any issues (wrong args, VRAM overflow, etc.)
4. --speed --memory for full fast phases
5. --coding for quality metrics
6. Review master_results.json diff
7. Ask user: "Apply CLAUDE.md updates?"
8. Commit all files (results JSON + per-model .md + CLAUDE.md)
```
