#!/usr/bin/env python3
"""Concurrent request benchmark for Ornith - tests parallel agent sub-requests."""

import json, time, sys, os, threading, concurrent.futures
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

API_URL = "http://127.0.0.1:8082/v1/chat/completions"
MODEL = "ornith-1.0-9b-Q5_K_M.gguf"
OUTPUT_DIR = "/home/barrak/Development/local-llms/benchmarks/outputs"

REQUESTS = [
    "Write a Python function to sort a list of dictionaries by a key",
    "Explain the difference between Redis and Memcached",
    "Write a bash one-liner to find the 10 largest files in a directory",
    "What is the time complexity of quicksort?",
    "Write a regex to validate email addresses",
    "Explain how TCP handshake works",
    "Write a git command to find all commits by a specific author",
    "What is the difference between Docker and Podman?",
    "Write a Python decorator that measures execution time",
    "Explain how B-trees work in databases",
]

def query(prompt, max_tokens=512):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.6,
        "stream": False,
    }).encode()
    req = Request(API_URL, data=payload, headers={"Content-Type": "application/json"})
    start = time.time()
    try:
        resp = urlopen(req, timeout=300)
        data = json.loads(resp.read())
        elapsed = time.time() - start
        usage = data.get("usage", {})
        return {
            "elapsed": round(elapsed, 2),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "output_len": len(data["choices"][0]["message"]["content"]),
            "error": None,
        }
    except Exception as e:
        return {"elapsed": time.time() - start, "error": str(e)}

def run_single():
    print("\n=== SINGLE REQUEST (baseline) ===")
    times = []
    for i, prompt in enumerate(REQUESTS[:5]):
        r = query(prompt)
        if r["error"]:
            print(f"  [{i+1}/5] ERROR: {r['error']}")
        else:
            tps = r["output_tokens"] / max(r["elapsed"] - 0.5, 0.1)
            print(f"  [{i+1}/5] {r['output_tokens']} tok in {r['elapsed']}s ({tps:.1f} t/s)")
            times.append(r)
    if times:
        avg = sum(t["elapsed"] for t in times) / len(times)
        avg_tok = sum(t["output_tokens"] for t in times) / len(times)
        print(f"  Avg: {avg_tok:.0f} tok in {avg:.2f}s ({avg_tok/max(avg-0.5,0.1):.1f} t/s)")

def run_concurrent(n):
    print(f"\n=== CONCURRENT ({n} parallel) ===")
    prompts = REQUESTS[:n]
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        results = list(ex.map(query, prompts))
    wall = time.time() - start
    ok = [r for r in results if not r["error"]]
    errs = [r for r in results if r["error"]]
    if errs:
        for e in errs:
            print(f"  ERROR: {e['error']}")
    if ok:
        total_tok = sum(r["output_tokens"] for r in ok)
        avg_lat = sum(r["elapsed"] for r in ok) / len(ok)
        agg_tps = total_tok / wall
        print(f"  {len(ok)}/{n} succeeded, {total_tok} total tok in {wall:.2f}s wall")
        print(f"  Avg latency: {avg_lat:.2f}s, Aggregate: {agg_tps:.1f} t/s")

def run_context():
    print("\n=== CONTEXT PROCESSING ===")
    sizes = [1000, 5000, 10000, 50000]
    for size in sizes:
        filler = "word " * size
        prompt = f"Summarize: {filler}\n\nWhat is this about?"
        r = query(prompt, max_tokens=128)
        if r["error"]:
            print(f"  {size:>6} tok: ERROR - {r['error']}")
        else:
            pt = r["prompt_tokens"]
            pp_tps = pt / max(r["elapsed"] - 0.2, 0.01)
            print(f"  {size:>6} fill → {pt:>6} prompt tok in {r['elapsed']:.2f}s ({pp_tps:.0f} t/s)")

if __name__ == "__main__":
    ts = datetime.now().isoformat()
    print(f"Concurrent Benchmark — {ts}")
    print(f"Model: {MODEL}")
    print(f"API: {API_URL}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    run_single()
    run_concurrent(2)
    run_concurrent(4)
    run_concurrent(8)

    print("\nDone.")
