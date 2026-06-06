---
name: remember
description: Save useful project or user context to PowerMem.
argument-hint: "[what to remember]"
user-invocable: true
---

Save useful context to PowerMem.

Use the `powermem` MCP server if it is available in Codex. Prefer `add_memory`
for new durable facts and `update_memory` only when the user identifies an
existing memory to correct.

Store information that will help future sessions: project conventions, setup
details, decisions, preferences, and recurring troubleshooting notes. Do not save
secrets, API keys, credentials, or transient command output.

If the MCP server is not available, run the status skill and explain that Codex
must be restarted after init so the installed plugin's bundled `.mcp.json` is
reloaded.
