Save useful context to PowerMem.

## Usage

```text
/remember [what to remember]
```

## Instructions

1. Extract the core fact, decision, preference, setup note, or troubleshooting
   result from the user's request.
2. Do not save secrets, API keys, access tokens, passwords, or transient command
   output.
3. Use the `add_memory` MCP tool from the `powermem` server.
4. Tag the memory with `agent_id: "opencode"` when the tool supports it.
5. Confirm the save and summarize what was stored.
