from __future__ import annotations

import json
from typing import Any, Callable


def prefix_topic(service_name: str, service_version: str, action_name: str) -> str:
    """Return the canonical subject prefix for a service action."""
    return f"v{service_version}.{service_name}.{action_name}"


def encode_json(payload: Any, default: Callable[[Any], Any] | None = None) -> bytes:
    """Serialize a payload to JSON bytes."""
    return json.dumps(payload, default=default).encode()


def decode_json(payload: bytes | str) -> Any:
    """Deserialize JSON data from bytes or string."""
    if isinstance(payload, bytes):
        payload = payload.decode()
    return json.loads(payload)
