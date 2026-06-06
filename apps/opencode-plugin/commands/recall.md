Recall relevant PowerMem memories for the current OpenCode task.

## Usage

```text
/recall [query]
```

## Instructions

1. Use the `search_memories` MCP tool from the `powermem` server.
2. Query with the user's provided text, or derive a concise query from the
   current task when no text is provided.
3. Use `limit: 10`.
4. Present only memories returned by the tool. Do not invent results.
5. If no results are returned, suggest two or three more specific search terms.
