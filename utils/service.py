from main import NatsBroker
from utils.action import ActionSchema


class CreateService:
    version: str = '1'
    name: str
    workers: int = 1
    actions: list[ActionSchema]

    def __init__(self, version, name, workers):
        self.actions = []
        self.version = version
        self.name = name
        self.workers = workers

    def add(self, **kwargs):
        actions = kwargs.get('actions')
        if isinstance(actions, list):
            self.actions.extend(actions)
        else:
            self.actions.append(actions)

    async def register(self, broker: NatsBroker):
        await broker.create_service(
            name=self.name,
            version=self.version,
            workers=self.workers,
            actions=self.actions,
        )
