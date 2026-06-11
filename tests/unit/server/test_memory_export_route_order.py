from server.api.v1.memories import router


def test_export_route_is_registered_before_memory_id_route():
    get_paths = [
        route.path
        for route in router.routes
        if "GET" in getattr(route, "methods", set())
    ]

    assert get_paths.index("/memories/export") < get_paths.index(
        "/memories/{memory_id}"
    )
