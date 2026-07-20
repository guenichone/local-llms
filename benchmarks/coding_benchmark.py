#!/usr/bin/env python3
"""Coding benchmark via local API — supports --api-url, --quant, --json-only flags"""

import argparse, json, time, sys, os
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

# Defaults — overridden by CLI flags
API_URL = "http://127.0.0.1:8082/v1/chat/completions"
MODEL = "unknown-model"
QUANT = "unknown"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")  # repo-relative
SUMMARY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "")        # results json next to us
JSON_ONLY = False

TASKS = [
    # ── Code generation ──
    {
        "name": "code-gen-fibonacci",
        "category": "code_generation",
        "description": "Memoized Fibonacci with good API design",
        "prompt": "Write a Python function `fibonacci(n: int) -> int` that returns the nth Fibonacci number using memoization. Include type hints, docstring, and a demonstrable example. Handle edge cases (negative n, 0, 1). Also add a `fibonacci_sequence(count: int) -> list[int]` that returns the first `count` numbers.",
    },
    {
        "name": "code-gen-json-validator",
        "category": "code_generation",
        "description": "JSON schema validator class",
        "prompt": "Write a Python class `JSONValidator` that can validate JSON data against a schema. Support these types: string, number, integer, boolean, array, object, null. Support constraints: required, minLength, maxLength, minimum, maximum, pattern (regex), enum. Include a `validate(data, schema) -> tuple[bool, list[str]]` method returning (is_valid, error_messages).",
    },
    {
        "name": "code-gen-file-parser",
        "category": "code_generation",
        "description": "Nginx log file parser with stats",
        "prompt": "Write a Python function `parse_nginx_log(filepath: str) -> dict` that parses an Nginx combined log format and returns stats: total_requests, unique_ips, status_code_counts, top_10_paths, hourly_request_counts. Use generators for memory efficiency on large files. Include type hints and a usage example.",
    },
    # ── Debugging ──
    {
        "name": "bug-finding-merge-intervals",
        "category": "debugging",
        "description": "Find bugs in merge_intervals",
        "prompt": """Find all bugs in this Python function and provide the corrected version:

```python
def merge_intervals(intervals):
    '''Merge overlapping intervals'''
    if not intervals:
        return intervals
    
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    
    for i in range(1, len(intervals)):
        current = intervals[i]
        last = merged[-1]
        
        if current[0] <= last[1]:
            last[1] = max(last[1], current[1])
        else:
            merged.append(current)
    
    return merged
```

List each bug with line number, severity (high/medium/low), and the fix.""",
    },
    {
        "name": "bug-finding-thread-safety",
        "category": "debugging",
        "description": "Find thread-safety bugs in cache",
        "prompt": """Find all thread-safety bugs in this Python caching class:

```python
import time

class TTLCache:
    def __init__(self, ttl_seconds=60):
        self._store = {}
        self._ttl = ttl_seconds
    
    def get(self, key):
        if key in self._store:
            value, expiry = self._store[key]
            if time.time() < expiry:
                return value
            del self._store[key]
        return None
    
    def set(self, key, value):
        self._store[key] = (value, time.time() + self._ttl)
    
    def cleanup(self):
        now = time.time()
        for key in list(self._store.keys()):
            _, expiry = self._store[key]
            if now >= expiry:
                del self._store[key]
    
    def size(self):
        return len(self._store)
```

List each bug with severity and the fix.""",
    },
    # ── Refactoring ──
    {
        "name": "refactor-eval",
        "category": "refactoring",
        "description": "Refactor eval-based code",
        "prompt": """Refactor this terrible code into something modern, safe, and well-structured:

```python
def process_data(d):
    import json
    x = eval(d['expr'])
    y = eval(d.get('filter', 'True'))
    r = []
    for i in range(len(x)):
        if eval(str(y).replace('x', str(x[i]))):
            r.append(x[i] * d.get('mult', 1))
    return json.dumps(r)
```

Requirements:
- Remove all eval() usage
- Add type hints
- Use proper error handling
- Make it testable
- Add clear error messages""",
    },
    {
        "name": "refactor-legacy-api",
        "category": "refactoring",
        "description": "Refactor messy legacy API handler",
        "prompt": """Refactor this messy Flask API handler into clean FastAPI code:

```python
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/api/v1/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        page = request.args.get('page', 1)
        limit = request.args.get('limit', 20)
        # get from db
        import sqlite3
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        offset = (int(page) - 1) * int(limit)
        c.execute(f"SELECT * FROM users LIMIT {limit} OFFSET {offset}")
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'no data'}), 400
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        c.execute(f"INSERT INTO users (name, email) VALUES ('{data['name']}', '{data['email']}')")
        conn.commit()
        conn.close()
        return jsonify({'id': c.lastrowid}), 201
```

Transform to FastAPI with: Pydantic models, async, dependency injection for DB, proper error handling, pagination model, SQL injection prevention.""",
    },
    # ── Testing ──
    {
        "name": "test-writing-log-parser",
        "category": "testing",
        "description": "pytest for log parser",
        "prompt": """Write comprehensive pytest tests for this function:

```python
from typing import Optional

def parse_log_line(line: str) -> Optional[dict]:
    '''Parse a log line like "[ERROR] 2024-01-15 10:30:00 - user123 - Failed login from 192.168.1.1"
    Returns dict with: level, timestamp, user_id, message, ip_address
    Returns None if parsing fails.'''
    import re
    pattern = r'^\[(\w+)\]\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+-\s+(\w+)\s+-\s+(.+?)(?:\s+from\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}))?$'
    m = re.match(pattern, line.strip())
    if not m:
        return None
    return {
        'level': m.group(1),
        'timestamp': m.group(2),
        'user_id': m.group(3),
        'message': m.group(4).strip(),
        'ip_address': m.group(5)
    }
```

Include tests for: valid lines, invalid lines, edge cases (no IP, empty string), and the function docstring examples.""",
    },
    {
        "name": "test-writing-rate-limiter",
        "category": "testing",
        "description": "pytest for token bucket rate limiter",
        "prompt": """Write comprehensive pytest tests (including concurrency tests) for this rate limiter:

```python
import time
import threading

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
```

Include tests for: basic consumption, refill timing, capacity limits, concurrent access, edge cases (zero tokens, high rate).""",
    },
    # ── Security ──
    {
        "name": "security-review",
        "category": "security",
        "description": "Find security vulnerabilities",
        "prompt": """Find all security vulnerabilities in this Python web app and provide fixes:

```python
from flask import Flask, request, render_template_string, make_response
import subprocess
import pickle
import base64

app = Flask(__name__)

@app.route('/')
def index():
    name = request.args.get('name', 'world')
    return render_template_string(f"<h1>Hello, {name}!</h1>")

@app.route('/admin/run')
def run_cmd():
    cmd = request.args.get('cmd')
    result = subprocess.check_output(cmd, shell=True)
    return result

@app.route('/api/data')
def get_data():
    data_b64 = request.cookies.get('session_data')
    if data_b64:
        data = pickle.loads(base64.b64decode(data_b64))
        return data
    return {'error': 'no data'}

@app.route('/flag')
def flag():
    resp = make_response("FLAG{debug}")
    resp.set_cookie('admin', 'false')
    return resp

if __name__ == '__main__':
    app.run(debug=True)
```

List each vulnerability with: CWE, severity, line number, exploit scenario, and fix.""",
    },
    # ── Optimization ──
    {
        "name": "optimization",
        "category": "optimization",
        "description": "Optimize slow data processing function",
        "prompt": """Optimize this slow Python function. The input is a list of 1M+ transactions. It should run in < 1s.

```python
from datetime import datetime

def process_transactions(transactions):
    '''transactions: list of dicts with keys: user_id, amount, timestamp, category'''
    result = {}
    for t in transactions:
        user = t['user_id']
        if user not in result:
            result[user] = {
                'total': 0,
                'count': 0,
                'categories': {},
                'first_txn': t['timestamp'],
                'last_txn': t['timestamp']
            }
        result[user]['total'] += t['amount']
        result[user]['count'] += 1
        cat = t['category']
        result[user]['categories'][cat] = result[user]['categories'].get(cat, 0) + 1
        if t['timestamp'] < result[user]['first_txn']:
            result[user]['first_txn'] = t['timestamp']
        if t['timestamp'] > result[user]['last_txn']:
            result[user]['last_txn'] = t['timestamp']
    return result
```

Identify performance issues and rewrite with optimizations. Explain each optimization.""",
    },
]

def query_model(prompt, max_tokens=4096, temp=0.6):
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert Python developer. Write correct, production-quality code."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temp,
        "top_p": 0.95,
        "stream": False
    }).encode()

    req = Request(API_URL, data=payload, headers={"Content-Type": "application/json"})
    
    start = time.time()
    try:
        resp = urlopen(req, timeout=300)
        ttft = time.time() - start
        data = json.loads(resp.read())
        elapsed = time.time() - start
        content = data["choices"][0]["message"]["content"]
        total_tokens = data["usage"]["total_tokens"]
        prompt_tokens = data["usage"]["prompt_tokens"]
        output_tokens = data["usage"]["completion_tokens"]
        timings = data.get("timings", {})
        gen_ms = timings.get("predicted_ms", 0)
        prompt_ms = timings.get("prompt_ms", 0)
        gen_tps = timings.get("predicted_per_second", 0)
        prompt_tps = timings.get("prompt_per_second", 0)
        return {
            "content": content,
            "ttft": ttft,
            "elapsed": elapsed,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "gen_time_s": gen_ms / 1000 if gen_ms else (output_tokens / gen_tps if gen_tps else elapsed - prompt_ms/1000),
            "prompt_time_s": prompt_ms / 1000 if prompt_ms else 0,
            "gen_tps": gen_tps if gen_tps else (output_tokens / max(elapsed - prompt_ms/1000, 0.001)),
            "prompt_tps": prompt_tps if prompt_tps else (prompt_tokens / max(prompt_ms/1000, 0.001)),
            "tokens_per_second": gen_tps or 0
        }
    except URLError as e:
        return {"error": str(e)}

def run_benchmarks():
    if not JSON_ONLY:
        print(f"Coding Benchmark — {QUANT}")
        print(f"Started: {datetime.now().isoformat()}")
        print(f"Model: {MODEL}")
        print(f"API: {API_URL}")
        print(f"{'='*70}")
    
    results = []
    total_prompt_tokens = 0
    total_output_tokens = 0
    total_latency = 0

    for task in TASKS:
        if not JSON_ONLY:
            print(f"\n{'─'*70}")
            print(f"[{task['category']}] {task['name']}: {task['description']}")
            print(f"{'─'*70}")
        
        result = query_model(task["prompt"])
        
        if "error" in result:
            if not JSON_ONLY:
                print(f"  ERROR: {result['error']}")
            results.append({"task": task["name"], "category": task["category"], "error": result["error"]})
            continue
        
        content = result["content"]
        
        if not JSON_ONLY:
            output_preview = content[:200].replace('\n', '\\n') + ("..." if len(content) > 200 else "")
            print(f"  Prompt: {result['prompt_tokens']} tok @ {result['prompt_tps']:.1f} t/s ({result['prompt_time_s']:.2f}s)")
            print(f"  Gen:    {result['output_tokens']} tok @ {result['gen_tps']:.1f} t/s ({result['gen_time_s']:.2f}s)")
            print(f"  TTFT:   {result['ttft']:.2f}s")
            print(f"  Total:  {result['elapsed']:.2f}s")
            print(f"  Output preview: {output_preview}")
        
        safe_name = f"{QUANT}-{task['name']}"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")
        with open(output_file, "w") as f:
            f.write(content)
        
        if not JSON_ONLY:
            print(f"  Saved: {output_file}")
        
        total_prompt_tokens += result["prompt_tokens"]
        total_output_tokens += result["output_tokens"]
        total_latency += result["elapsed"]
        
        results.append({
            "task": task["name"],
            "category": task["category"],
            "description": task["description"],
            "ttft": round(result["ttft"], 2),
            "elapsed": round(result["elapsed"], 2),
            "prompt_time_s": round(result["prompt_time_s"], 2),
            "gen_time_s": round(result["gen_time_s"], 2),
            "prompt_tokens": result["prompt_tokens"],
            "output_tokens": result["output_tokens"],
            "prompt_tps": round(result["prompt_tps"], 1),
            "gen_tps": round(result["gen_tps"], 1),
            "output_len": len(content)
        })
    
    # Compute aggregates
    avg_ttft = sum(r["ttft"] for r in results if "ttft" in r) / max(len(results), 1)
    avg_gen_tps = sum(r["gen_tps"] for r in results if "gen_tps" in r) / max(len(results), 1)
    avg_prompt_tps = sum(r["prompt_tps"] for r in results if "prompt_tps" in r) / max(len(results), 1)
    avg_gen_time = sum(r["gen_time_s"] for r in results if "gen_time_s" in r) / max(len(results), 1)
    avg_output_tokens = sum(r["output_tokens"] for r in results if "output_tokens" in r) / max(len(results), 1)
    
    summary = {
        "model": MODEL,
        "quant": QUANT,
        "timestamp": datetime.now().isoformat(),
        "total_tasks": len(TASKS),
        "completed": len(results),
        "total_prompt_tokens": total_prompt_tokens,
        "total_output_tokens": total_output_tokens,
        "total_time_seconds": round(total_latency, 2),
        "avg_ttft": round(avg_ttft, 2),
        "avg_gen_tps": round(avg_gen_tps, 1),
        "avg_prompt_tps": round(avg_prompt_tps, 1),
        "avg_gen_time_s": round(avg_gen_time, 2),
        "avg_output_tokens": round(avg_output_tokens, 0),
        "results": results
    }
    
    summary_file = os.path.join(SUMMARY_DIR, f"results_{QUANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    if JSON_ONLY:
        print(json.dumps(summary, indent=2))
    else:
        print(f"\n{'='*70}")
        print(f"SUMMARY — {QUANT}")
        print(f"{'='*70}")
        print(f"Tasks: {len(results)} / {len(TASKS)} completed")
        print(f"Total prompt tokens: {total_prompt_tokens}")
        print(f"Total output tokens: {total_output_tokens}")
        print(f"Total time: {total_latency:.2f}s")
        print(f"Avg TTFT:              {avg_ttft:.2f}s")
        print(f"Avg prompt t/s:        {avg_prompt_tps:.1f}")
        print(f"Avg gen t/s:           {avg_gen_tps:.1f}")
        print(f"Avg gen time:          {avg_gen_time:.2f}s")
        print(f"Avg output tokens:     {avg_output_tokens:.0f}")
        print(f"\nResults saved: {summary_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coding benchmark for local LLMs")
    parser.add_argument("--api-url", default="http://127.0.0.1:8082/v1",
                        help="Base API URL (e.g. http://127.0.0.1:8082/v1)")
    parser.add_argument("--quant", default="Q5_K_M",
                        help="Quant label for output naming (e.g. Q5_K_M)")
    parser.add_argument("--model", default="local-model",
                        help="Model name sent in API request payload")
    parser.add_argument("--json-only", action="store_true",
                        help="Output summary as JSON to stdout (machine-readable)")
    parser.add_argument("--output-dir", default=None,
                        help="Directory for raw output .txt files")
    parser.add_argument("--summary-dir", default=None,
                        help="Directory for results JSON file")
    args = parser.parse_args()
    
    API_URL = args.api_url.rstrip("/") + "/chat/completions"
    MODEL = args.model
    QUANT = args.quant
    JSON_ONLY = args.json_only
    
    if args.output_dir:
        OUTPUT_DIR = args.output_dir
    if args.summary_dir:
        SUMMARY_DIR = args.summary_dir
    
    run_benchmarks()
