import type { Plugin } from "@opencode-ai/plugin";

const MARKETPLACE_ROOT = "/home/barrak/Development/dev-ai-claude-code-marketplace";

export default (() => {
  return {
    "shell.env": (_input: any, output: { env?: Record<string, string> }) => {
      output.env = {
        ...output.env,
        CLAUDE_PLUGIN_ROOT: MARKETPLACE_ROOT,
      };
    },
  };
}) satisfies Plugin;
