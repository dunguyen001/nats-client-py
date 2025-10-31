from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol


class ActionHandler(Protocol):
    async def __call__(self, context: dict[str, Any]) -> Any:
        ...


class Validator(Protocol):
    def __call__(self, **payload: Any) -> Any:
        ...


@dataclass(slots=True)
class ActionSchema:
    """Describe an action that can be registered against the broker."""

    name: str
    handle: ActionHandler
    queue: bool = True
    validate: Optional[Validator] = None
