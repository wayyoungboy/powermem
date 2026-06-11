from unittest.mock import MagicMock

import pytest

starlette_requests = pytest.importorskip("starlette.requests")

from server.api.v1.memories import list_memories  # noqa: E402

Request = starlette_requests.Request


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
