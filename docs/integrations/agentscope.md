# AgentScope

Use PowerMem as a long-term memory tool provider for AgentScope agents through
AgentScope's MCP client support. This keeps the integration lightweight:
PowerMem owns memory storage and retrieval, while AgentScope registers the
PowerMem MCP tools into its `Toolkit`.

AgentScope supports HTTP and stdio MCP servers, stateful and stateless MCP
clients, and registering MCP tools into `Toolkit`. PowerMem exposes the same
memory tools through `powermem-mcp`, so no AgentScope-specific storage adapter is
required.

## Prerequisites

- PowerMem installed with MCP support:

```bash
pip install "powermem[mcp]"
```

- PowerMem configured with your storage, LLM, and embedding providers.
- AgentScope installed in the application environment.

## Start PowerMem MCP

Use streamable HTTP for a long-running local or remote AgentScope process:

```bash
powermem-mcp streamable-http 8848
```

PowerMem serves MCP at:

```text
http://localhost:8848/mcp
```

If your AgentScope process should launch PowerMem itself, stdio is also
available:

```bash
powermem-mcp stdio
```

## Register PowerMem tools in AgentScope

```python
import asyncio

from agentscope.mcp import HttpStatelessClient
from agentscope.tool import Toolkit


async def build_toolkit() -> Toolkit:
    toolkit = Toolkit()
    powermem = HttpStatelessClient(
        name="powermem",
        transport="streamable_http",
        url="http://localhost:8848/mcp",
    )

    await toolkit.register_mcp_client(powermem, group_name="memory")
    return toolkit


toolkit = asyncio.run(build_toolkit())
print([tool["function"]["name"] for tool in toolkit.get_json_schemas()])
```

The registered tools include the standard PowerMem MCP memory operations:

- `add_memory`
- `search_memories`
- `get_memory_by_id`
- `update_memory`
- `delete_memory`
- `delete_all_memories`
- `list_memories`

Pass the resulting `toolkit` to the AgentScope agent or workflow that should be
able to remember and recall information.

## Function-level calls

AgentScope can also obtain a single callable MCP tool by name. This is useful
when a workflow wants explicit memory read/write steps instead of registering all
tools.

```python
import asyncio

from agentscope.mcp import HttpStatelessClient


async def search_powermem() -> None:
    powermem = HttpStatelessClient(
        name="powermem",
        transport="streamable_http",
        url="http://localhost:8848/mcp",
    )

    search_memories = await powermem.get_callable_function(
        func_name="search_memories",
        wrap_tool_result=True,
    )

    result = await search_memories(
        query="dragonfruit-zx9",
        user_id="agentscope-demo-user",
        limit=5,
    )
    print(result)


asyncio.run(search_powermem())
```

## Verify

1. Start `powermem-mcp streamable-http 8848`.
2. Run the AgentScope snippet above.
3. Confirm `search_memories` and `add_memory` appear in
   `toolkit.get_json_schemas()`.
4. Add a probe memory with `add_memory` and search for the same token with
   `search_memories`.

## Troubleshooting

- If AgentScope cannot list tools, confirm `http://localhost:8848/mcp` matches
  the PowerMem MCP transport and port.
- If memory calls fail, validate the PowerMem `.env` first. The MCP server
  depends on the same storage, LLM, and embedding configuration as the Python SDK.
- If the AgentScope process runs in a different shell or container, pass the same
  PowerMem environment variables there, including `POWERMEM_API_KEY` when auth is
  enabled.
- Use the generic [MCP client guide](./mcp_client.md) for stdio, SSE, and auth
  variations.

## References

- AgentScope MCP tutorial: https://doc.agentscope.io/tutorial/task_mcp.html
- PowerMem MCP guide: ./mcp_client.md
