#!/usr/bin/env node
/**
 * Lightweight proxy: Claude Code  ->  OpenRouter
 * Translates Claude's internal model names to OpenRouter's format.
 *
 * Example:
 *   claude-opus-4-8[1m]  ->  anthropic/claude-opus-4.8
 *   claude-sonnet-4-5    ->  anthropic/claude-sonnet-4.5
 *
 * Usage:
 *   node or-proxy.mjs                # start on :8099
 *   ANTHROPIC_BASE_URL=http://localhost:8099 claude ...
 */

import http from "node:http";
import { request } from "node:https";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const DIR = dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.OR_PROXY_PORT || "8099");
const OR_HOST = "openrouter.ai";

const MODEL_MAP = {
  // Anthropic
  "claude-opus-4-8":       "anthropic/claude-opus-4.8",
  "claude-opus-4-8-fast":  "anthropic/claude-opus-4.8-fast",
  "claude-opus-4-7":       "anthropic/claude-opus-4.7",
  "claude-opus-4-7-fast":  "anthropic/claude-opus-4.7-fast",
  "claude-opus-4-6":       "anthropic/claude-opus-4.6",
  "claude-opus-4-5":       "anthropic/claude-opus-4.5",
  "claude-sonnet-5":       "anthropic/claude-sonnet-5",
  "claude-sonnet-4-6":     "anthropic/claude-sonnet-4.6",
  "claude-sonnet-4-5":     "anthropic/claude-sonnet-4.5",
  "claude-haiku-4-5":      "anthropic/claude-haiku-4.5",
  "claude-haiku-4":        "anthropic/claude-3-haiku",
  "claude-fable-5":        "anthropic/claude-fable-5",
  // Dated model variants (Claude Code sub-agents use these)
  "claude-haiku-4-5-20251001": "anthropic/claude-haiku-4.5",
  "claude-opus-4-8-20250219":  "anthropic/claude-opus-4.8",
  "claude-sonnet-5-20250601":  "anthropic/claude-sonnet-5",
  "claude-fable-5-20250702":   "anthropic/claude-fable-5",
  // DeepSeek
  "deepseek-v4-pro":       "deepseek/deepseek-v4-pro",
  "deepseek-v4-flash":     "deepseek/deepseek-v4-flash",
  "ds-pro":                "deepseek/deepseek-v4-pro",
  "ds-flash":              "deepseek/deepseek-v4-flash",
  "dsf":                   "deepseek/deepseek-v4-flash",
  "dsp":                   "deepseek/deepseek-v4-pro",
  // Qwen
  "qwen3.6-27b":           "qwen/qwen3.6-27b",
  "qwen3.6-flash":         "qwen/qwen3.6-flash",
  "qwf":                   "qwen/qwen3.6-flash",
  "qwen-coder":            "qwen/qwen3-coder-plus",
  "qwc":                   "qwen/qwen3-coder-plus",
  // GLM
  "glm-5.2":               "z-ai/glm-5.2",
  "glm5":                  "z-ai/glm-5.2",
  // Google
  "gemini-flash":          "google/gemini-2.5-flash",
  "gemini-pro":            "google/gemini-2.5-pro",
  // When user passes any other name, it forwards as-is (OpenRouter pass-through)
};

function loadKey() {
  for (const dir of [DIR, resolve(DIR, ".."), process.cwd()]) {
    const envFile = resolve(dir, ".env");
    if (existsSync(envFile)) {
      for (const line of readFileSync(envFile, "utf-8").split("\n")) {
        const m = line.match(/^OPENROUTER_API_KEY=(.+)/);
        if (m) return m[1].trim();
      }
    }
  }
  return null;
}

const OR_KEY = loadKey();
if (!OR_KEY) {
  console.error("OPENROUTER_API_KEY not found in .env");
  process.exit(1);
}

http.createServer((req, res) => {
  let body = [];
  req.on("data", c => body.push(c));
  req.on("end", () => {
    let bodyStr = Buffer.concat(body).toString();
    let translated = false;

    if (bodyStr) {
      try {
        const json = JSON.parse(bodyStr);
        const raw = json.model || "";
        let stripped = raw.replace("[1m]", "");
        let mapped = MODEL_MAP[stripped];
        // Fuzzy match: strip date suffix (-YYYYMMDD) for dated model variants
        if (!mapped) {
          const baseName = stripped.replace(/-\d{8}$/, "");
          mapped = MODEL_MAP[baseName];
          if (mapped) console.error(`[or-proxy] fuzzy match: ${stripped} -> ${mapped}`);
        }
        if (mapped) {
          json.model = mapped;
          bodyStr = JSON.stringify(json);
          translated = true;
        }
      } catch { /* non-JSON body pass-through */ }
    }

    const targetPath = req.url.replace(/^\/v1/, "/api/v1");
    const opts = {
      hostname: OR_HOST,
      path: targetPath,
      method: req.method,
      headers: {
        "Authorization": `Bearer ${OR_KEY}`,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "content-length": Buffer.byteLength(bodyStr),
      },
    };

    const orReq = request(opts, orRes => {
      // Forward streaming responses as-is
      res.writeHead(orRes.statusCode, orRes.headers);
      orRes.pipe(res);
    });
    orReq.on("error", e => { res.writeHead(502); res.end(e.message); });
    orReq.end(bodyStr);
    if (translated) console.error(`[or-proxy] ${JSON.parse(bodyStr).model}`);
  });
}).listen(PORT, "127.0.0.1", () => {
  console.error(`OR proxy :${PORT}  ->  OpenRouter`);
});
