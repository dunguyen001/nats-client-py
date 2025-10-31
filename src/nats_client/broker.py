from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Iterable, Sequence

import nats
from nats.aio.client import Client, Msg
from nats.aio.subscription import Subscription

from .schema import ActionSchema
from .utils import decode_json, encode_json, prefix_topic

logger = logging.getLogger(__name__)

Context = dict[str, Any]
RequestFn = Callable[[str, Any, int], Awaitable[dict[str, Any]]]
SubscriptionHandler = Callable[[Context], Awaitable[None]]


class NatsBroker:
    """Lightweight helper around the async NATS client."""

    def __init__(
        self,
        servers: Sequence[str] | str = ("nats://localhost:4222",),
        token: str | None = None,
    ) -> None:
        self.servers = [servers] if isinstance(servers, str) else list(servers)
        self.token = token
        self.nc: Client | None = None
        self.is_done: asyncio.Future[bool] | None = None

    async def connect(self) -> None:
        """Connect to NATS and set the global client reference."""
        try:
            loop = asyncio.get_running_loop()
            self.is_done = loop.create_future()
            self.nc = await nats.connect(
                servers=self.servers,
                token=self.token,
                closed_cb=self.closed_cb,
            )
        except Exception as exc:  # pragma: no cover - relies on NATS runtime
            logger.exception("Failed to connect to NATS servers %s", self.servers, exc_info=exc)
            raise

    async def closed_cb(self) -> None:
        logger.warning("Connection to NATS is closed.")
        if self.is_done and not self.is_done.done():
            self.is_done.set_result(True)

    def emit(self) -> RequestFn:
        async def emit_handle(topic: str, payload: Any, timeout: int = 10_000) -> dict[str, Any]:
            return await self.request(topic, payload, timeout=timeout)

        return emit_handle

    async def call(self, topic: str, payload: Any, timeout: int = 10_000) -> dict[str, Any]:
        return await self.request(topic, payload, timeout=timeout)

    async def request(self, topic: str, payload: Any, *, timeout: int = 10_000) -> dict[str, Any]:
        nc = self._require_client()
        message = await nc.request(
            subject=topic,
            payload=encode_json(payload=payload, default=_default_json_serializer),
            timeout=timeout,
        )
        response: dict[str, Any] = decode_json(message.data)
        if not response.get("ok"):
            raise RuntimeError(response.get("message"))
        return response

    async def publish(
        self,
        subject: str,
        payload: Any,
        *,
        reply: str | None = None,
        headers: dict[str, str] | None = None,
        flush: bool = False,
    ) -> None:
        """Publish a message without awaiting a reply."""

        nc = self._require_client()
        await nc.publish(
            subject=subject,
            payload=encode_json(payload, default=_default_json_serializer),
            reply=reply,
            headers=headers,
        )
        if flush:
            await nc.flush()

    async def subscribe(
        self,
        subject: str,
        handler: SubscriptionHandler,
        *,
        queue: str | None = None,
        decoder: Callable[[bytes], Any] | None = decode_json,
    ) -> Subscription:
        """Register a pub/sub handler for a given subject."""

        nc = self._require_client()

        async def _callback(msg: Msg) -> None:
            payload = msg.data if decoder is None else decoder(msg.data)
            ctx = self._context(msg=msg, payload=payload)
            await handler(ctx)

        queue_arg = queue or ""
        return await nc.subscribe(subject=subject, queue=queue_arg, cb=_callback)

    @staticmethod
    async def unsubscribe(subscription: Subscription, max_msgs: int | None = None) -> None:
        """Unsubscribe from a subscription returned by :meth:`subscribe`."""

        if max_msgs is None:
            await subscription.unsubscribe()
        else:
            await subscription.unsubscribe(limit=max_msgs)

    def _assert_connected(self) -> None:
        if not self.nc or not self.nc.is_connected:
            raise RuntimeError("NATS client is not connected.")

    def _require_client(self) -> Client:
        self._assert_connected()
        assert self.nc is not None
        return self.nc

    async def create_service(
        self,
        version: str,
        name: str,
        workers: int = 1,
        actions: Iterable[ActionSchema] | None = None,
    ) -> None:
        nc = self._require_client()
        if actions is None:
            actions = []

        for action in actions:
            for worker_id in range(workers):
                subject = prefix_topic(
                    service_name=name,
                    service_version=version,
                    action_name=action.name,
                )
                queue = f"{subject}-{worker_id}" if action.queue else None
                await nc.subscribe(
                    subject=subject,
                    queue=queue,
                    cb=self._prefix_action(action),
                )
                logger.info("[%s] Registered topic", subject)

    def _prefix_action(self, action: ActionSchema):
        async def msg_handle(msg: Msg):
            try:
                payload = decode_json(msg.data)
                ctx = self._context(msg=msg, payload=payload)
                if action.validate:
                    ctx["payload"] = action.validate(**payload).dict()

                result = await action.handle(ctx)

                if msg.reply:
                    await msg.respond(encode_json({"ok": True, "result": result}))
            except Exception as exc:  # pragma: no cover - requires broker runtime
                logger.exception("Handler for %s failed", action.name, exc_info=exc)
                if msg.reply:
                    await msg.respond(encode_json({"ok": False, "message": str(exc)}))

        return msg_handle

    def _context(self, *, msg: Msg | None = None, payload: Any | None = None) -> Context:
        ctx: Context = {
            "broker": self._require_client(),
            "emit": self.emit(),
        }
        if msg is not None:
            ctx["msg"] = msg
        if payload is not None:
            ctx["payload"] = payload
        return ctx


def _default_json_serializer(obj):
    if hasattr(obj, "__json__"):
        return obj.__json__()
    raise TypeError(f"Object of type {type(obj)!r} is not JSON serializable")
