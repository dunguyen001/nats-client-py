from __future__ import annotations

import asyncio
import json
import typing

import nats
from nats.aio.client import Client, Msg

nats_server = nats
nats_client = None


class ActionSchema:
    def __init__(self, name, handle, queue: bool = True, validate=None):
        self.name = name
        self.handle = handle
        self.queue = queue
        self.validate = validate


def prefix_topic(service_name, service_version, action_name):
    return "v{version}.{name}.{action_name}".format(
        version=service_version,
        name=service_name,
        action_name=action_name,
    )


def encode_json(payload):
    return json.dumps(payload, default=lambda o: o.__json__()).encode()


def decode_json(payload):
    return json.loads(payload)


class NatsBroker:
    nc: Client = None
    is_done = asyncio.Future()

    def __init__(self, servers: str | list[str] = ["nats://localhost:4222"], token: str = None):
        self.servers = servers
        self.token = token

    async def connect(self):
        try:
            self.nc = await nats_server.connect(
                **{"servers": self.servers, "token": self.token, "closed_cb": self.closed_cb, })

            global nats_client
            nats_client = self.nc
        except Exception as e:
            print(e)

    async def closed_cb(self):
        print('Connection to NATS is closed.')
        self.is_done.set_result(True)

    def emit(self):
        ctx = self

        async def emit_handle(topic, payload, timeout=10000):
            try:
                ctx.server_is_live()
                m = await ctx.nc.request(
                    subject=topic,
                    payload=encode_json(payload=payload),
                    timeout=timeout
                )
                response = decode_json(m.data)
                if not response['ok']:
                    raise Exception(response['message'])
                return response
            except Exception as e:
                raise e

        return emit_handle

    async def call(self, topic, payload, timeout=10000):
        res = await self.emit()(topic, payload, timeout)
        return res

    def server_is_live(self):
        if not self.nc.is_connected:
            self.closed_cb()

    async def create_service(self, version, name, workers=1, actions: typing.List[ActionSchema] = []):
        self.server_is_live()

        for action in actions:
            for i in range(workers):
                topic_name = prefix_topic(
                    service_name=name,
                    service_version=version,
                    action_name=action.name,
                )
                await self.nc.subscribe(
                    subject=topic_name,
                    queue="{0}-{1}".format(topic_name, i) if action.queue else None,
                    cb=self._prefix_action(action),
                )
                print("[{0}]: Registered topic".format(topic_name))

    def _prefix_action(self, action: ActionSchema):
        async def msg_handle(msg: Msg):
            try:
                subject = msg.subject
                reply = msg.reply
                data = msg.data.decode()
                action_name = subject.split(".")[2]
                if action_name != action.name:
                    return None

                ctx = self._context()
                ctx['payload'] = decode_json(data)

                if action.validate:
                    ctx['payload'] = action.validate(**decode_json(data)).dict()

                result = await action.handle(ctx)

                if len(reply):
                    await msg.respond(encode_json({"ok": True, "result": result}))
            except Exception as e:
                if len(msg.reply):
                    await msg.respond(encode_json({"ok": False, "message": str(e)}))
                print(e)

        return msg_handle

    def _context(self):
        return {
            "broker": self.nc,
            "emit": self.emit(),
        }


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
