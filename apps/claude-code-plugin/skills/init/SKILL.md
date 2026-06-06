---
description: Initialize PowerMem for Claude Code after the plugin is installed. Use when the user asks to set up, initialize, or repair PowerMem.
---

Initialize PowerMem for Claude Code.

0. If this skill was just installed and is not available yet, tell the user to run `/reload-plugins` or restart Claude Code, then retry `/memory-powermem:init`.
1. Run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/status.sh"` if `CLAUDE_PLUGIN_ROOT` is available; otherwise locate the installed plugin root and run `scripts/status.sh`.
2. If the backend is healthy, tell the user PowerMem is ready and include the base URL.
3. If configuration is missing, ask only for missing values:
   - `LLM_PROVIDER` such as `anthropic`, `openai`, `qwen`, `deepseek`, `ollama`, or `vllm`
   - `LLM_MODEL`
   - `LLM_API_KEY`, unless the provider is `ollama` or `vllm`
   - optional custom base URL
4. Run `scripts/init.sh`. If values were collected, pass them as environment variables:
   - `POWERMEM_INIT_LLM_PROVIDER`
   - `POWERMEM_INIT_LLM_MODEL`
   - `POWERMEM_INIT_LLM_API_KEY`
   - `POWERMEM_INIT_LLM_BASE_URL`
   - `POWERMEM_INIT_PACKAGE` when the user wants to test unpublished backend code instead of the PyPI `powermem[server,mcp,seekdb]` package.
5. Never print API keys. Mask secrets in summaries.
6. After init succeeds, run `scripts/status.sh` again and report the base URL.
