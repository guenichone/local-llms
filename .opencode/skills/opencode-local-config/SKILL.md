---
name: opencode-local-config
description: |
  Use when managing opencode provider/model config for local llama.cpp servers,
  or when the user asks about local model selection, running models, or adding
  new local models to opencode. Do NOT use for cloud provider configuration.
---

# OpenCode Local Model Configuration

## Overview

This repo has two local llama.cpp servers that opencode can use:

| Port | Provider | Default Model |
|---|---|---|
| 8080 | `local` | Qwen3.6-27B MTP |
| 8082 | `ornith` | Ornith-1.0-9B Q5_K_M |

Both providers are configured in `opencode.json` with static model listings.
OpenCode's TUI model picker (`opencode` → model select) shows all configured
models. Select one and press enter to start a session.

## Quick Commands

```bash
code               # opencode TUI — pick any model
code ornith        # Ornith Q5 (local, port 8082)
code local         # Qwen3.6-27B MTP (local, port 8080)
code status        # show running servers + all configured models
code ds            # DeepSeek V4 Flash (OpenRouter)
code glm           # GLM 5.2 (OpenRouter)
```

## Viewing Available Models

```bash
code status
```

This runs `scripts/model-status.sh` which:
1. Queries each local server's `/v1/models` to show what's currently running
2. Lists all configured models from `opencode.json` with their provider and base URL

## Adding a New Local Model

1. Place the GGUF file in `~/models/<model-name>/`
2. Start the server (usually on port 8080 or 8082, or a new port)
3. Add a new provider entry in `opencode.json`, or add the model to an existing provider's `models` list:

```json
{
  "provider": {
    "my-provider": {
      "name": "My Model (local)",
      "api": "openai",
      "options": {
        "baseURL": "http://127.0.0.1:<port>/v1",
        "apiKey": "not-needed"
      },
      "models": {
        "model-filename.gguf": {
          "name": "Display Name",
          "tool_call": true,
          "limit": { "context": 32768, "output": 8192 }
        }
      }
    }
  }
}
```

4. Add a short alias to `~/.zshrc.d/providers.zsh` and tab completion
5. Add a script in `scripts/` to start the server if needed
6. Restart opencode to pick up the new config

## Provider Naming Convention

- Provider key must match what `code` alias maps to: `code ornith` → `ornith/...`
- Model selector in opencode TUI shows models as `provider/model-id`
- Model ID is the key in the `models` object (usually the GGUF filename)
