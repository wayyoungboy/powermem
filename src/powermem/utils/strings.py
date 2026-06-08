from typing import Any


def strip_wrapping_quotes(value: Any) -> Any:
    """Strip one matching quote pair preserved by env/config loaders.

    This keeps compatibility with Docker-style env files that pass quoted
    values through literally. Passwords that intentionally start and end with
    the same quote character should be configured without wrapper syntax.
    """
    if not isinstance(value, str):
        return value

    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return value
