---
name: recall
description: Recall relevant PowerMem memories for the current task.
argument-hint: "[search query]"
user-invocable: true
---

Recall relevant memories from PowerMem.

Use the `powermem` MCP server if it is available in Codex. Prefer
`search_memories` with a concise query derived from the user's current task.

If the MCP server is not available, run the status skill and explain that Codex
must be restarted after init so the installed plugin's bundled `.mcp.json` is
reloaded.

Summarize only the relevant memories. Do not dump raw memory payloads unless the
user asks for them.
