from __future__ import annotations

from typing import Iterable, List, Sequence

from .broker import NatsBroker
from .schema import ActionSchema


class CreateService:
    """Collect and register actions against a broker instance."""

    def __init__(self, version: str, name: str, workers: int = 1) -> None:
        self.version = version
        self.name = name
        self.workers = workers
        self.actions: list[ActionSchema] = []

    def add(self, **kwargs) -> None:
        new_actions = kwargs.get("actions")
        if isinstance(new_actions, list):
            self.actions.extend(new_actions)
        elif new_actions is not None:
            self.actions.append(new_actions)

    async def register(self, broker: NatsBroker) -> None:
        await broker.create_service(
            name=self.name,
            version=self.version,
            workers=self.workers,
            actions=self.actions,
        )
