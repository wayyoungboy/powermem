from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from powermem.core.memory import Memory
from powermem.storage.adapter import StorageAdapter
from powermem.storage.sqlite.sqlite_vector_store import SQLiteVectorStore
from server.api.v1.memories import list_memories
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
    assert [memory["memory"] for memory in page] == ["personal-2", "personal-3"]
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
    service.memory.get_all.return_value = {"results": [{"id": 1, "memory": "m"}]}
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


@pytest.mark.asyncio
async def test_list_memories_api_converts_scope_to_metadata_filter():
    service = MagicMock()
    service.count_memories.return_value = 1
    service.list_memories.return_value = [
        {
            "id": 1,
            "memory": "remember scope",
            "user_id": "u01",
            "agent_id": "a01",
            "metadata": {"scope": "personal"},
        }
    ]

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/memories",
            "headers": [],
            "query_string": b"",
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )

    response = await list_memories(
        request=request,
        user_id="u01",
        agent_id="a01",
        scope="personal",
        limit=100,
        offset=0,
        sort_by=None,
        order="desc",
        time_range=None,
        api_key="test-key",
        service=service,
    )

    assert response.success is True
    assert response.data["total"] == 1
    service.count_memories.assert_called_once_with(
        user_id="u01",
        agent_id="a01",
        filters={"scope": "personal"},
    )
    service.list_memories.assert_called_once_with(
        user_id="u01",
        agent_id="a01",
        limit=100,
        offset=0,
        sort_by=None,
        order="desc",
        filters={"scope": "personal"},
    )
