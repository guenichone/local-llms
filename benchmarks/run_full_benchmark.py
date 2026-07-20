#!/usr/bin/env python3
"""
Full model benchmark driver: speed (llama-bench), memory (nvidia-smi + /proc/meminfo),
coding quality (11-task), and normalized storage (master_results.json + per-model .md).

Usage:
  # Speed + memory (default, fast)
  run_full_benchmark.py --model ornith-1.0-9b --quant Q5_K_M

  # Speed only
  run_full_benchmark.py --model ornith-1.0-9b --quant Q5_K_M --speed-only

  # All phases
  run_full_benchmark.py --model ornith-1.0-9b --quant Q5_K_M --all

  # List available models
  run_full_benchmark.py --list
"""

import argparse, json, os, re, shlex, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "benchmarks" / "outputs"
MODELS_DIR = REPO_ROOT / "benchmarks" / "models"
MASTER_RESULTS = REPO_ROOT / "benchmarks" / "master_results.json"
CODING_BENCH = REPO_ROOT / "benchmarks" / "coding_benchmark.py"
LLAMA_BENCH_VANILLA = Path.home() / "llama.cpp" / "build" / "bin" / "llama-bench"
LLAMA_BENCH_TURBO = Path.home() / "llama-cpp-turboquant" / "build-turbo" / "bin" / "llama-bench"
LLAMA_SERVER_VANILLA = Path.home() / "llama.cpp" / "build" / "bin" / "llama-server"
LLAMA_SERVER_TURBO = Path.home() / "llama-cpp-turboquant" / "build-turbo" / "bin" / "llama-server"
CUDA_LIB = Path.home() / ".local" / "cuda-12.8" / "lib64"

# ── Model Registry ───────────────────────────────────────────────────────────
# Each entry documents a model family. Quants define which GGUF files are
# available. server_args are the default flags used to start llama-server for
# that model (must match providers.zsh for consistency).
MODEL_REGISTRY = {
    "ornith-1.0-9b": {
        "name": "Ornith-1.0-9B",
        "family": "qwen35",
        "model_dir": "~/models/ornith-1.0-9b",
        "quants": {
            "Q4_K_M": {"file": "ornith-1.0-9b-Q4_K_M.gguf", "size_gb": 5.3},
            "Q5_K_M": {"file": "ornith-1.0-9b-Q5_K_M.gguf", "size_gb": 6.1},
            "Q6_K":   {"file": "ornith-1.0-9b-Q6_K.gguf", "size_gb": 7.2},
        },
        "build": "vanilla",
        "port": 8082,
        "context_max": 200000,
        "server_args": {
            "vanilla": (
                "-ngl 99 -t 6 --port {port} --host 127.0.0.1 "
                "--temp 0.6 --top-p 0.95 --top-k 20 "
                "-ub 4096 -b 4096 --cache-reuse 256 "
                "--flash-attn on --reasoning-preserve "
                "--cache-type-k q8_0 --cache-type-v q8_0 "
                "-np 6 --kv-unified"
            ),
        },
        "llama_bench_args": "-fa on",
        "external_scores": {"swe_bench_verified": 69.4, "terminal_bench": 43.1},
        "notes": "Best quant for 16GB: Q5_K_M. Vanilla build + flash-attn is optimal.",
        "references": {
            "huggingface": [
                "https://huggingface.co/collections/deepreinforce-ai/ornith-10",
                "https://huggingface.co/bartowski/deepreinforce-ai_Ornith-1.0-9B-GGUF",
                "https://huggingface.co/s-batman/Ornith-1.0-9B-NVFP4-MTP-GGUF",
            ],
            "articles": [
                "https://deep-reinforce.com/ornith_1_0.html",
                "https://codersera.com/blog/how-to-run-ornith-1-0-locally-2026/",
            ],
            "videos": [],
            "github": [],
        },
    },
    "qwen3.6-27b": {
        "name": "Qwen3.6-27B MTP",
        "family": "qwen36",
        "model_dir": "~/models",
        "quants": {
            "Q3_K_S": {"file": "qwen3.6-27b-mtp-Q3_K_S.gguf", "size_gb": 12.0},
        },
        "build": "turboquant",
        "port": 8080,
        "context_max": 200000,
        "server_args": {
            "turboquant": (
                "-ngl 99 -t 4 --port {port} --host 127.0.0.1 "
                "--temp 0.7 --top-p 0.95 --top-k 40 "
                "--spec-type draft-mtp --spec-draft-n-max 2 "
                "--flash-attn on "
                "-ctk q8_0 -ctv turbo3 "
                "-np 1"
            ),
        },
        "llama_bench_args": "-fa on -ctk q8_0 -ctv turbo3",
        "external_scores": {"swe_bench_verified": None, "terminal_bench": None},
        "notes": "Uses turboquant build for 200K ctx on single 5080. MTP gives ~2x gen speed.",
        "references": {
            "huggingface": [],
            "articles": [
                "https://codersera.com/blog/how-to-run-qwen-3-6-locally-2026/",
            ],
            "videos": [],
            "github": [
                "https://github.com/TheTom/llama-cpp-turboquant",
            ],
        },
    },
    "qwopus-35b-nano": {
        "name": "Qwopus 35B Nano",
        "family": "qwopus",
        "model_dir": "~/models/qwopus",
        "quants": {
            "Nano": {"file": "Qwopus3.6-35B-A3B-v1-APEX-MTP-I-Nano.gguf", "size_gb": 10.9},
        },
        "build": "turboquant",
        "port": 8083,
        "context_max": 131072,
        "server_args": {
            "turboquant": (
                "-ngl 99 -t 8 --port {port} --host 127.0.0.1 "
                "--temp 0.6 --top-p 0.95 --top-k 20 "
                "--repeat-penalty 1.1 --dry-multiplier 0.5 --dry-allowed-length 3 --dry-penalty-last-n 4096 "
                "-ub 4096 -b 4096 --cache-reuse 256 "
                "--flash-attn on "
                "-ctk q8_0 -ctv turbo3 "
                "--reasoning-budget 2048 "
                "-np 1 -fit off"
            ),
        },
        "llama_bench_args": "-fa on -ctk q8_0 -ctv turbo3",
        "external_scores": {"swe_bench_verified": None, "terminal_bench": None},
        "notes": "Opus reasoning traces fine-tune. -fit off required (MTP hang). 165 t/s tg128.",
        "references": {
            "huggingface": [
                "https://huggingface.co/mudler",
            ],
            "articles": [],
            "videos": [],
            "github": [
                "https://github.com/TheTom/llama-cpp-turboquant",
            ],
        },
    },
    "gemma4-4b": {
        "name": "Gemma 4 E4B",
        "family": "gemma4",
        "model_dir": "~/models/gemma4-4b",
        "quants": {
            "Q4_K_M": {"file": "gemma-4-E4B-it-Q4_K_M.gguf", "size_gb": 3.0},
        },
        "build": "vanilla",
        "port": 8084,
        "context_max": 32768,
        "server_args": {
            "vanilla": (
                "-ngl 99 -t 8 --port {port} --host 127.0.0.1 "
                "--chat-template gemma "
                "--temp 0.7 --top-p 0.95 "
                "-ub 2048 -b 2048 --cache-reuse 256 "
                "-np 2"
            ),
        },
        "llama_bench_args": "--chat-template gemma",
        "external_scores": {"swe_bench_verified": None, "terminal_bench": None},
        "notes": "Only ~3GB. Fits alongside other models. Fast, no reasoning overhead.",
        "references": {
            "huggingface": [],
            "articles": [],
            "videos": [],
            "github": [],
        },
    },
    "ornith-35b-mini": {
        "name": "Ornith-1.0-35B Mini",
        "family": "qwen35",
        "model_dir": "~/models/ornith-1.0-35b",
        "quants": {
            "Mini": {"file": "ornith-1.0-35b-APEX-Mini.gguf", "size_gb": 12.5},
        },
        "build": "vanilla",
        "port": 8085,
        "context_max": 60000,
        "server_args": {
            "vanilla": (
                "-ngl 99 -t 8 --port {port} --host 127.0.0.1 "
                "--temp 0.6 --top-p 0.95 --top-k 20 "
                "-ub 4096 -b 4096 --cache-reuse 256 "
                "--flash-attn on --reasoning-preserve "
                "--cache-type-k q8_0 --cache-type-v q8_0 "
                "-np 1"
            ),
        },
        "llama_bench_args": "-fa on",
        "external_scores": {"swe_bench_verified": 75.6, "terminal_bench": 64.2},
        "notes": "Best SWE-bench score for local models but only ~60K ctx on 16GB.",
        "references": {
            "huggingface": [
                "https://huggingface.co/collections/deepreinforce-ai/ornith-10",
                "https://huggingface.co/mudler",
            ],
            "articles": [
                "https://deep-reinforce.com/ornith_1_0.html",
            ],
            "videos": [],
            "github": [],
        },
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _expand(path_str):
    """Expand ~ and return resolved Path."""
    return Path(path_str).expanduser().resolve()


def _run(cmd, **kwargs):
    """Run command, return stdout. Raises on error unless check=False."""
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{CUDA_LIB}:{env.get('LD_LIBRARY_PATH', '')}"
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=kwargs.pop("timeout", 300), env=env, **kwargs
    )
    if "check" not in kwargs or kwargs["check"]:
        result.check_returncode()
    # suppress nvidia-smi stderr noise in wsl
    return result.stdout.strip()


def _gpu_name():
    """Return GPU model string from nvidia-smi."""
    try:
        return _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    except Exception:
        return "unknown"


def _gpu_vram_info():
    """Return (total_mb, used_mb, free_mb) from nvidia-smi."""
    try:
        out = _run(["nvidia-smi", "--query-gpu=memory.total,memory.used,memory.free",
                     "--format=csv,noheader,nounits"])
        total, used, free = map(int, out.split(","))
        return total, used, free
    except Exception:
        return 0, 0, 0


def _system_ram_info():
    """Return (total_kb, available_kb, free_kb) from /proc/meminfo."""
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                mem[k.strip()] = int(v.strip().split()[0])
    return mem["MemTotal"], mem.get("MemAvailable", mem["MemFree"]), mem["MemFree"]


def _is_server_running(port):
    """Check if llama-server is answering on a port."""
    import urllib.request, urllib.error
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3)
        return True
    except Exception:
        return False


def _kill_server(port):
    """Kill any process listening on port."""
    try:
        out = _run(["lsof", "-ti", f":{port}"], check=False)
        if out:
            for pid in out.splitlines():
                os.kill(int(pid), 15)
            time.sleep(2)
    except Exception:
        pass


def _start_server(model_path, server_bin, server_args_str, port, context=131072):
    """Start llama-server, wait for readiness, return PID."""
    logfile = f"/tmp/llama-bench-{port}-{os.getpid()}.log"
    log_fh = open(logfile, "w")
    cmd = shlex.split(f"{server_bin} -m {model_path} {server_args_str} -c {context}")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{CUDA_LIB}:{env.get('LD_LIBRARY_PATH', '')}"
    proc = subprocess.Popen(cmd, env=env, stdout=log_fh, stderr=log_fh,
                           start_new_session=True)
    # Wait for readiness
    for i in range(40):
        if _is_server_running(port):
            return proc.pid, logfile
        time.sleep(1.5)
    # Timeout — kill and report
    try:
        os.kill(proc.pid, 15)
    except Exception:
        pass
    log_fh.close()
    raise RuntimeError(f"Server failed to start within 60s. Log: {logfile}")


def _stop_server(pid):
    """Kill server process by PID."""
    try:
        os.kill(pid, 15)
    except OSError:
        pass
    time.sleep(2)


# ── Phase 1: Speed (llama-bench) ─────────────────────────────────────────────

def _run_llama_bench(bench_bin, model_path, ngl, threads, flash_attn, cache_kv=None,
                      extra_args="", prompt=512, gen=128, reps=3):
    """Run llama-bench once and return avg_ts for pp + tg."""
    extra = extra_args or ""
    if flash_attn and "--flash-attn" not in extra and "-fa" not in extra:
        extra += " --flash-attn on"
    cmd = (
        f"{bench_bin} -m {model_path} -ngl {ngl} -t {threads} "
        f"-p {prompt} -n {gen} -r {reps} --no-warmup -o json {extra}"
    )
    try:
        raw = _run(cmd, timeout=180)
        results = json.loads(raw)
        # Return dict: {pp_t_s: N, tg_t_s: N, ...}
        return _extract_speed(results)
    except Exception as e:
        return {"error": str(e)}


def _extract_speed(results_json):
    """Parse llama-bench JSON output list into speed dict."""
    pp, tg = None, None
    for r in results_json:
        if r.get("n_gen", 0) == 0:
            pp = r["avg_ts"]
        else:
            tg = r["avg_ts"]
    return {"pp_t_s": pp, "tg_t_s": tg, "model_size": results_json[0].get("model_size", 0)}


def run_speed_benchmarks(cfg, quant):
    """Run speed sweep for a model + quant and return structured dict."""
    model_path = _expand(cfg["model_dir"]) / cfg["quants"][quant]["file"]
    build = cfg["build"]
    bench_bin = LLAMA_BENCH_TURBO if build == "turboquant" else LLAMA_BENCH_VANILLA
    extra = cfg.get("llama_bench_args", "")

    if not bench_bin.exists():
        return {"error": f"llama-bench not found: {bench_bin}"}
    if not model_path.exists():
        return {"error": f"Model not found: {model_path}"}

    def _b(ngl, t, fa=True, extra_args=""):
        e = f"{extra} {extra_args}".strip()
        return _run_llama_bench(bench_bin, model_path, ngl, t, fa, extra_args=e)

    results = {}

    # Full GPU
    results["ngl99_t4_fa_on"] = _b(99, 4)
    results["ngl99_t6_fa_on"] = _b(99, 6)
    results["ngl99_t8_fa_on"] = _b(99, 8)

    # Flash-attn off comparison
    results["ngl99_t6_fa_off"] = _b(99, 6, fa=False)

    # Cache type variants (vanilla build only — turboquant uses turbo3)
    if build == "vanilla" and "turboquant" not in str(bench_bin):
        results["ngl99_t6_fa_on_kv_q8_0"] = _b(99, 6, extra_args="-ctk q8_0 -ctv q8_0")
        results["ngl99_t6_fa_on_kv_q4_0"] = _b(99, 6, extra_args="-ctk q4_0 -ctv q4_0")

    # All CPU baseline
    results["ngl0_t6"] = _b(0, 6, fa=False)

    # MTP draft sweep (if applicable)
    if "--spec-type" in cfg["server_args"].get(build, ""):
        results["ngl99_t4_mtp"] = _b(99, 4, extra_args="--spec-type draft-mtp --spec-draft-n-max 2")

    return results


# ── Phase 2: Memory ──────────────────────────────────────────────────────────

def _snapshot():
    """Capture (vram_used_mb, vram_free_mb, ram_avail_kb)."""
    total_v, used_v, free_v = _gpu_vram_info()
    total_r, avail_r, free_r = _system_ram_info()
    return {
        "vram_total_mb": total_v,
        "vram_used_mb": used_v,
        "vram_free_mb": free_v,
        "ram_total_kb": total_r,
        "ram_available_kb": avail_r,
        "ram_free_kb": free_r,
    }


def _compute_kv_cache_bytes(ctx, n_layers, n_kv_heads, head_dim, k_type, v_type):
    """Theoretical KV cache size in bytes for a given context length and types.
    
    type_ratios: 'f16'→2.0, 'q8_0'→0.5625 (9/16), 'q4_0'→0.375 (6/16), 'turbo3'→0.4375
    """
    type_bytes = {"f16": 2.0, "q8_0": 9 / 16, "q4_0": 6 / 16, "turbo3": 7 / 16}
    k_bytes = type_bytes.get(k_type, 0.5)
    v_bytes = type_bytes.get(v_type, 0.5)
    per_position = n_layers * n_kv_heads * head_dim * (k_bytes + v_bytes)
    return int(ctx * per_position)


def run_memory_benchmarks(cfg, quant):
    """Measure VRAM/RAM footprint at baseline and at max context."""
    model_path = _expand(cfg["model_dir"]) / cfg["quants"][quant]["file"]
    model_size_gb = cfg["quants"][quant]["size_gb"]
    build = cfg["build"]
    port = cfg["port"]
    ctx_max = cfg["context_max"]
    server_bin = LLAMA_SERVER_TURBO if build == "turboquant" else LLAMA_SERVER_VANILLA
    server_args_template = cfg["server_args"].get(build, cfg["server_args"].get("vanilla", ""))
    server_args = server_args_template.format(port=port)

    if not server_bin.exists():
        return {"error": f"llama-server not found: {server_bin}"}

    # Kill anything on the port and wait for VRAM to settle
    _kill_server(port)
    time.sleep(3)
    snap_baseline = _snapshot()

    # Start server at max context (single run for peak footprint)
    pid, log = _start_server(model_path, server_bin, server_args, port, context=ctx_max)
    time.sleep(5)  # Let CUDA allocator stabilize
    snap_maxctx = _snapshot()

    # Stop server
    _stop_server(pid)
    time.sleep(2)
    _kill_server(port)

    # Compute deltas
    vram_delta = snap_maxctx["vram_used_mb"] - snap_baseline["vram_used_mb"]
    ram_delta = snap_baseline["ram_available_kb"] - snap_maxctx["ram_available_kb"]

    # Model VRAM ≈ file size (GGUF is memory-mapped, size ≈ GPU memory used)
    model_vram_mb = int(model_size_gb * 1024)
    kvcache_vram_mb = vram_delta - model_vram_mb

    return {
        "baseline": snap_baseline,
        "loaded_ctx_max": snap_maxctx,
        "vram_delta_mb": vram_delta,
        "model_vram_mb_est": model_vram_mb,
        "kvcache_vram_mb_est": kvcache_vram_mb,
        "ram_delta_kb": ram_delta,
        "context_max": ctx_max,
    }


# ── Phase 3: Coding Quality ─────────────────────────────────────────────────

def run_coding_benchmarks(cfg, quant):
    """Run the 11-task coding benchmark via API."""
    port = cfg["port"]
    api_url = f"http://127.0.0.1:{port}/v1"

    if not _is_server_running(port):
        return {"error": f"No server on port {port}. Start it first with --start-server."}

    cmd = [
        sys.executable, str(CODING_BENCH),
        "--api-url", api_url,
        "--quant", quant,
        "--json-only",
    ]
    try:
        raw = _run(cmd, timeout=900)
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


# ── Phase 4: Normalize & Store ───────────────────────────────────────────────

def _load_master():
    """Load master_results.json, return empty dicts if missing."""
    if MASTER_RESULTS.exists():
        with open(MASTER_RESULTS) as f:
            return json.load(f)
    return {"meta": {}, "entries": {}}


def _save_master(data):
    """Write master_results.json atomically."""
    tmp = MASTER_RESULTS.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(MASTER_RESULTS)


def normalize_and_store(cfg, quant, speed_results, memory_results, coding_results):
    """Combine all phases, write per-run JSON, update master, update per-model .md."""
    model_key = cfg.get("_key", "unknown")
    entry_key = f"{model_key}/{quant}/{cfg['build']}"

    # Gather external scores
    external = cfg.get("external_scores", {})

    # Best speed numbers
    best_speed = {}
    for k, v in (speed_results or {}).items():
        if v and "pp_t_s" in v:
            best_speed[k] = {"pp_t_s": v["pp_t_s"], "tg_t_s": v["tg_t_s"]}

    entry = {
        "model": cfg["name"],
        "model_key": model_key,
        "family": cfg.get("family", ""),
        "architecture": cfg.get("architecture", ""),
        "quant": quant,
        "model_size_gb": cfg["quants"][quant]["size_gb"],
        "build": cfg["build"],
        "port": cfg["port"],
        "context_max": cfg.get("context_max"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": best_speed,
        "memory": memory_results,
        "coding_bench": coding_results,
        "external_scores": external,
        "references": cfg.get("references", {}),
        "notes": cfg.get("notes", ""),
    }

    # Write per-run JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    per_run_file = REPO_ROOT / "benchmarks" / f"results_{model_key}_{quant}_{ts}.json"
    with open(per_run_file, "w") as f:
        json.dump(entry, f, indent=2)

    # Update master
    master = _load_master()
    master["meta"] = master.get("meta", {})
    master["meta"]["gpu"] = _gpu_name()
    master["meta"]["cuda"] = "12.8.57"
    master["meta"]["os"] = "WSL2 Ubuntu 24.04"
    master["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    master["entries"] = master.get("entries", {})
    master["entries"][entry_key] = entry
    _save_master(master)

    # Update per-model .md
    _update_model_md(cfg, entry)

    return entry, per_run_file


def _update_model_md(cfg, entry):
    """Append/update timestamped entry to benchmarks/models/<model>.md."""
    model_key = cfg.get("_key", "unknown")
    md_file = MODELS_DIR / f"{model_key}.md"

    summary_lines = [f"## Benchmark Run — {entry['timestamp'][:19]}"]
    summary_lines.append(f"- **Quant:** {entry['quant']} ({entry['model_size_gb']} GB)")
    summary_lines.append(f"- **Build:** {entry['build']}")

    speed = entry.get("speed", {})
    if speed:
        summary_lines.append("- **Speed:**")
        for k, v in sorted(speed.items()):
            pp = f"{v['pp_t_s']:.0f}" if v.get("pp_t_s") else "N/A"
            tg = f"{v['tg_t_s']:.1f}" if v.get("tg_t_s") else "N/A"
            summary_lines.append(f"  - {k}: pp={pp} t/s, tg={tg} t/s")

    mem = entry.get("memory", {})
    if mem and "vram_delta_mb" in mem:
        summary_lines.append(f"- **VRAM:** delta={mem['vram_delta_mb']} MB, "
                             f"model={mem.get('model_vram_mb_est','?')} MB, "
                             f"kv cache={mem.get('kvcache_vram_mb_est','?')} MB "
                             f"@ctx={mem.get('context_max','?')}")

    coding = entry.get("coding_bench", {})
    if coding and "total_tasks" in coding:
        summary_lines.append(f"- **Coding:** {coding.get('completed','?')}/{coding.get('total_tasks','?')} tasks")

    summary_lines.append(f"- **Result file:** `benchmarks/results_{model_key}_{entry['quant']}_{entry['timestamp'][:10].replace('-','')}*.json`")

    refs = entry.get("references", {})
    if any(refs.values()):
        summary_lines.append("- **References:**")
        if refs.get("huggingface"):
            for url in refs["huggingface"]:
                summary_lines.append(f"  - [HF] {url}")
        if refs.get("articles"):
            for url in refs["articles"]:
                summary_lines.append(f"  - [Article] {url}")
        if refs.get("videos"):
            for url in refs["videos"]:
                summary_lines.append(f"  - [Video] {url}")
        if refs.get("github"):
            for url in refs["github"]:
                summary_lines.append(f"  - [Repo] {url}")

    summary_lines.append("")

    if md_file.exists():
        content = md_file.read_text()
        # Insert new run before the ## Model Info section (if present), otherwise append
        if "## Model Info" in content:
            idx = content.index("## Model Info")
            content = content[:idx] + "\n".join(summary_lines) + "\n" + content[idx:]
        else:
            content = content + "\n" + "\n".join(summary_lines)
    else:
        content = f"# {cfg['name']}\n\n" + "\n".join(summary_lines)
        content += f"\n## Model Info\n- **Family:** {cfg.get('family','?')}\n"
        content += f"- **External scores:** {json.dumps(cfg.get('external_scores',{}))}\n"
        content += f"- **Notes:** {cfg.get('notes','')}\n"

    md_file.write_text(content)


# ── CLAUDE.md Diff ───────────────────────────────────────────────────────────

def _generate_claude_table_rows(master):
    """Generate table rows for CLAUDE.md from master_results."""
    rows = []
    for key, e in master.get("entries", {}).items():
        speed = e.get("speed", {})
        # Pick best speed: prefer ngl99 with fa_on, any thread count
        best_key = None
        for k in sorted(speed.keys()):
            if "ngl99" in k and "fa_on" in k:
                best_key = k
        if not best_key:
            for k in sorted(speed.keys()):
                if "ngl99" in k:
                    best_key = k
        best_full = speed.get(best_key or "", {})
        pp = best_full.get("pp_t_s", 0)
        tg = best_full.get("tg_t_s", 0)
        pp_str = f"{pp:.0f}" if pp else "—"
        tg_str = f"{tg:.1f}" if tg else "—"
        ctx = e.get("context_max", "?")
        ext = e.get("external_scores", {})
        swe = ext.get("swe_bench_verified", "")
        tb = ext.get("terminal_bench", "")
        swe_str = f"{swe}%" if swe else "—"
        tb_str = f"{tb}%" if tb else "—"
        rows.append(
            f"| {e['model']} {e['quant']} | {e['model_size_gb']} GB | {pp_str} | {tg_str} | "
            f"{ctx} | {swe_str} | {tb_str} |"
        )
    return rows


def show_claude_diff():
    """Print proposed CLAUDE.md table rows from master_results."""
    master = _load_master()
    rows = _generate_claude_table_rows(master)
    if not rows:
        print("No entries in master_results.json yet.")
        return
    header = "| Model | Size | pp8192 | tg128 | ctx max | SWE-bench | Term-Bench |"
    sep = "|---|---|---|---|---|---|---|"
    print(header)
    print(sep)
    for r in rows:
        print(r)
    print(f"\n{len(rows)} entries. Add to CLAUDE.md under '## Complete Benchmarks' section.")


# ── Main ─────────────────────────────────────────────────────────────────────

def _resolve_cfg(model_key):
    """Find model config, return dict with _key set."""
    if model_key not in MODEL_REGISTRY:
        print(f"Unknown model '{model_key}'. Available:")
        for k in sorted(MODEL_REGISTRY):
            print(f"  {k}")
        sys.exit(1)
    cfg = dict(MODEL_REGISTRY[model_key])
    cfg["_key"] = model_key
    return cfg


def _resolve_quant(cfg, quant):
    """Validate quant exists in model config."""
    if quant not in cfg["quants"]:
        print(f"Unknown quant '{quant}' for {cfg['name']}. Available:")
        for k, v in cfg["quants"].items():
            print(f"  {k} ({v['size_gb']} GB)")
        sys.exit(1)


def _countdown(seconds, label="Starting in"):
    """Print countdown."""
    for i in range(seconds, 0, -1):
        print(f"  {label} {i}s...", end="\r")
        time.sleep(1)
    print(" " * 40, end="\r")


def _ensure_server(cfg, quant, port):
    """Start server if not already running on port."""
    model_path = _expand(cfg["model_dir"]) / cfg["quants"][quant]["file"]
    build = cfg["build"]
    server_bin = LLAMA_SERVER_TURBO if build == "turboquant" else LLAMA_SERVER_VANILLA
    server_args_template = cfg["server_args"].get(build, cfg["server_args"].get("vanilla", ""))
    server_args = server_args_template.format(port=port)

    if _is_server_running(port):
        print(f"  Server already on :{port}")
        return

    # Kill others to free VRAM (only one big model at a time)
    for other_port in [8080, 8082, 8083, 8084, 8085]:
        if other_port != port:
            _kill_server(other_port)
    time.sleep(1)

    print(f"  Starting server on :{port}...")
    pid, log = _start_server(model_path, server_bin, server_args, port, context=cfg.get("context_max", 131072))
    print(f"  Server ready (PID {pid})")


def main():
    parser = argparse.ArgumentParser(description="Full model benchmark driver")
    parser.add_argument("--model", help="Model key from registry (e.g. ornith-1.0-9b)")
    parser.add_argument("--quant", help="Quant key (e.g. Q5_K_M)")
    parser.add_argument("--list", action="store_true", help="List available models and quants")
    parser.add_argument("--speed-only", action="store_true")
    parser.add_argument("--memory-only", action="store_true")
    parser.add_argument("--coding-only", action="store_true")
    parser.add_argument("--all", action="store_true", help="Run all three phases")
    parser.add_argument("--coding", action="store_true", help="Include coding benchmark")
    parser.add_argument("--no-store", action="store_true", help="Skip writing results to files")
    parser.add_argument("--diff-claude", action="store_true", help="Show proposed CLAUDE.md table rows")
    parser.add_argument("--start-server", action="store_true", help="Auto-start server for coding benchmarks")
    parser.add_argument("--port", type=int, help="Override default port")
    args = parser.parse_args()

    # List mode
    if args.list:
        print("Model Registry:")
        for key, cfg in sorted(MODEL_REGISTRY.items()):
            quants_str = ", ".join(f"{k} ({v['size_gb']}GB)" for k, v in cfg["quants"].items())
            print(f"  {key}  [{cfg['build']}]  {quants_str}")
            print(f"    port={cfg['port']}  ctx_max={cfg.get('context_max','?')}")
            if cfg.get("external_scores", {}).get("swe_bench_verified"):
                print(f"    SWE-bench={cfg['external_scores']['swe_bench_verified']}%  "
                      f"Terminal-bench={cfg['external_scores'].get('terminal_bench','?')}")
        return

    # Diff mode
    if args.diff_claude:
        show_claude_diff()
        return

    # Benchmark mode
    if not args.model or not args.quant:
        parser.error("--model and --quant required for benchmarking. Use --list to see options.")

    cfg = _resolve_cfg(args.model)
    _resolve_quant(cfg, args.quant)

    if args.port:
        cfg["port"] = args.port

    # Determine which phases to run
    run_speed = args.speed_only or args.all or (not args.memory_only and not args.coding_only)
    run_memory = args.memory_only or args.all or (not args.speed_only and not args.coding_only)
    run_coding = args.coding_only or args.coding or args.all

    # Edge: speed-only and memory-only both set → run both
    if args.speed_only and args.memory_only:
        run_speed = run_memory = True

    if not any([run_speed, run_memory, run_coding]):
        # Default: speed + memory
        run_speed = run_memory = True

    print(f"Benchmark: {cfg['name']} — {args.quant}")
    print(f"  Build: {cfg['build']}  |  Port: {cfg['port']}  |  Context max: {cfg.get('context_max', '?')}")
    print(f"  Phases: {'speed ' if run_speed else ''}{'memory ' if run_memory else ''}{'coding ' if run_coding else ''}")
    print(f"{'='*60}")

    speed_results = None
    memory_results = None
    coding_results = None

    # ── Speed ──
    if run_speed:
        print("\n── Phase 1: Speed (llama-bench) ──")
        speed_results = run_speed_benchmarks(cfg, args.quant)
        if speed_results.get("error"):
            print(f"  ERROR: {speed_results['error']}")
        else:
            for k, v in sorted(speed_results.items()):
                pp = f"{v['pp_t_s']:.0f}" if v.get("pp_t_s") else "N/A"
                tg = f"{v['tg_t_s']:.1f}" if v.get("tg_t_s") else "N/A"
                print(f"  {k:30s}  pp={pp:>7s} t/s  tg={tg:>7s} t/s")

    # ── Memory ──
    if run_memory:
        print("\n── Phase 2: Memory ──")
        _countdown(3, "Killing existing servers in")
        for p in [cfg["port"]]:
            _kill_server(p)
        time.sleep(1)
        memory_results = run_memory_benchmarks(cfg, args.quant)
        if memory_results.get("error"):
            print(f"  ERROR: {memory_results['error']}")
        else:
            print(f"  Baseline VRAM used:  {memory_results['baseline']['vram_used_mb']} MB")
            print(f"  Peak VRAM used:      {memory_results['loaded_ctx_max']['vram_used_mb']} MB")
            print(f"  VRAM delta:          {memory_results['vram_delta_mb']} MB")
            print(f"  Model VRAM (est):    {memory_results['model_vram_mb_est']} MB")
            print(f"  KV cache VRAM (est): {memory_results['kvcache_vram_mb_est']} MB")
            print(f"  RAM delta:           {memory_results['ram_delta_kb']//1024} MB")

    # ── Coding ──
    if run_coding:
        print("\n── Phase 3: Coding Benchmark ──")
        if args.start_server:
            _ensure_server(cfg, args.quant, cfg["port"])
        coding_results = run_coding_benchmarks(cfg, args.quant)
        if coding_results.get("error"):
            print(f"  ERROR: {coding_results['error']}")
        else:
            print(f"  Tasks: {coding_results.get('completed','?')}/{coding_results.get('total_tasks','?')}")
            print(f"  Avg TTFT:       {coding_results.get('avg_ttft','?'):.1f}s" if coding_results.get('avg_ttft') else "  (no timing data)")
            print(f"  Avg gen t/s:    {coding_results.get('avg_gen_tps','?'):.1f}" if coding_results.get('avg_gen_tps') else "")
            print(f"  Avg prompt t/s: {coding_results.get('avg_prompt_tps','?'):.1f}" if coding_results.get('avg_prompt_tps') else "")

    # ── Store ──
    if not args.no_store and any([speed_results, memory_results, coding_results]):
        print("\n── Phase 4: Store ──")
        entry, per_run_file = normalize_and_store(cfg, args.quant, speed_results, memory_results, coding_results)
        print(f"  Per-run:  {per_run_file}")
        print(f"  Master:   {MASTER_RESULTS}")
        print(f"  Model MD: {MODELS_DIR / f'{args.model}.md'}")
        print(f"\n── Proposed CLAUDE.md Table Row ──")
        _print_single_row(entry)

    print(f"\n{'='*60}")
    print("Done.")


def _print_single_row(entry):
    """Print a CLAUDE.md table row for a single entry."""
    speed = entry.get("speed", {})
    # Pick best available ngl99 with fa_on
    best = {}
    for k in sorted(speed.keys()):
        if "ngl99" in k and "fa_on" in k:
            best = speed[k]
    if not best:
        for k in sorted(speed.keys()):
            if "ngl99" in k:
                best = speed[k]
    pp = f"{best['pp_t_s']:.0f}" if best.get("pp_t_s") else "—"
    tg = f"{best['tg_t_s']:.1f}" if best.get("tg_t_s") else "—"
    ctx = entry.get("context_max", "?")
    ext = entry.get("external_scores", {})
    swe = ext.get("swe_bench_verified", "")
    tb = ext.get("terminal_bench", "")
    swe_str = f"{swe}%" if swe else "—"
    tb_str = f"{tb}%" if tb else "—"
    print(f"| {entry['model']} {entry['quant']} | {entry['model_size_gb']} GB | {pp} | {tg} | {ctx} | {swe_str} | {tb_str} |")


if __name__ == "__main__":
    main()
