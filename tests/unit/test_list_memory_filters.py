import asyncio
from unittest.mock import AsyncMock, MagicMock

from powermem.core.async_memory import AsyncMemory
from powermem.core.memory import Memory
from powermem.storage.adapter import StorageAdapter
from powermem.storage.sqlite.sqlite_vector_store import SQLiteVectorStore
from server.services.memory_service import MemoryService


def _add_memory(adapter, content, scope):
    return adapter.add_memory(
        {
            "content": content,
            "user_id": "u01",
            "agent_id": "a01",
            "metadata": {"scope": scope},
        }
    )


def test_storage_adapter_filters_metadata_before_pagination():
    store = SQLiteVectorStore(database_path=":memory:")
    adapter = StorageAdapter(store)

    _add_memory(adapter, "personal-1", "personal")
    _add_memory(adapter, "group-1", "group")
    _add_memory(adapter, "personal-2", "personal")
    _add_memory(adapter, "personal-3", "personal")

    total = adapter.count_all_memories(
        user_id="u01",
        agent_id="a01",
        filters={"scope": "personal"},
    )
    page = adapter.get_all_memories(
        user_id="u01",
        agent_id="a01",
        limit=2,
        offset=1,
        sort_by="id",
        order="asc",
        filters={"scope": "personal"},
    )

    assert total == 3
    assert [memory["memory"] for memory in page] == [
        "personal-2",
        "personal-3",
    ]
    assert all(memory["metadata"]["scope"] == "personal" for memory in page)


def test_memory_count_all_passes_filters_to_storage():
    memory = Memory.__new__(Memory)
    memory.storage = MagicMock()
    memory.storage.count_all_memories.return_value = 2
    memory.audit = MagicMock()

    result = memory.count_all(
        user_id="u01",
        agent_id="a01",
        filters={"scope": "personal"},
    )

    assert result == 2
    memory.storage.count_all_memories.assert_called_once_with(
        "u01",
        "a01",
        None,
        filters={"scope": "personal"},
    )


def test_memory_service_list_and_count_pass_filters():
    service = MemoryService.__new__(MemoryService)
    service.memory = MagicMock()
    service.memory.get_all.return_value = {
        "results": [{"id": 1, "memory": "m"}]
    }
    service.memory.count_all.return_value = 1

    listed = service.list_memories(
        user_id="u01",
        agent_id="a01",
        filters={"scope": "group"},
    )
    counted = service.count_memories(
        user_id="u01",
        agent_id="a01",
        filters={"scope": "group"},
    )

    assert listed == [{"id": 1, "memory": "m"}]
    assert counted == 1
    service.memory.get_all.assert_called_once_with(
        user_id="u01",
        agent_id="a01",
        limit=100,
        offset=0,
        filters={"scope": "group"},
        sort_by=None,
        order="desc",
    )
    service.memory.count_all.assert_called_once_with(
        user_id="u01",
        agent_id="a01",
        filters={"scope": "group"},
    )


def test_memory_get_all_keeps_graph_relations_out_of_results():
    memory = Memory.__new__(Memory)
    memory.storage = MagicMock()
    memory.audit = MagicMock()
    memory.enable_graph = True
    memory.graph_store = MagicMock()
    memory._http_client = None
    memory.agent_id = None

    stored_memory = {
        "id": 1,
        "memory": "personal-1",
        "metadata": {"scope": "personal"},
    }
    relation = {"source": "u01", "relationship": "likes", "target": "topic"}
    memory.storage.get_all_memories.return_value = [stored_memory]
    memory.graph_store.get_all.return_value = [relation]

    result = memory.get_all(user_id="u01", agent_id="a01", limit=10, offset=0)

    assert result["results"] == [stored_memory]
    assert result["relations"] == [relation]
    memory.graph_store.get_all.assert_called_once_with(
        {"user_id": "u01", "agent_id": "a01", "run_id": None}, 10
    )


def test_async_memory_get_all_keeps_graph_relations_out_of_results():
    async def run_test():
        memory = AsyncMemory.__new__(AsyncMemory)
        memory.storage = MagicMock()
        memory.audit = MagicMock()
        memory.audit.log_event_async = AsyncMock()
        memory.enable_graph = True
        memory.graph_store = MagicMock()

        stored_memory = {
            "id": 1,
            "memory": "personal-1",
            "metadata": {"scope": "personal"},
        }
        relation = {
            "source": "u01",
            "relationship": "likes",
            "target": "topic",
        }
        memory.storage.get_all_memories_async = AsyncMock(
            return_value=[stored_memory]
        )
        memory.graph_store.get_all.return_value = [relation]

        result = await memory.get_all(
            user_id="u01",
            agent_id="a01",
            limit=10,
            offset=0,
        )

        assert result["results"] == [stored_memory]
        assert result["relations"] == [relation]
        memory.graph_store.get_all.assert_called_once_with(
            {"user_id": "u01", "agent_id": "a01", "run_id": None}, 10
        )

    asyncio.run(run_test())
