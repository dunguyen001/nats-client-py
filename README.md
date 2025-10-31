# nats-client-py

Lightweight helper utilities for wiring Python microservices to a NATS
message broker. The package focuses on request/reply style interactions
and keeps the API surface intentionally small so you can compose it with
your preferred web frameworks or worker runtimes.

## Features at a Glance
- Async NATS broker wrapper (`NatsBroker`) that manages connections,
  request/reply calls, pub/sub helpers, and graceful shutdown hooks.
- Declarative action registration via `ActionSchema` and
  `CreateService`, supporting optional validation and queue groups.
- Compatibility shim for legacy `client` imports while using a modern
  `src/` package layout.

## Installation
```bash
python -m pip install -e .
# or install from a package index / artifact once published
```

The package requires Python 3.10+ and currently pins `nats-py==2.11.0`.
Remember to run a NATS server locally before testing. Docker example:

```bash
docker run --rm -p 4222:4222 nats:2.10-alpine
```

## Quick Start
```python
from nats_client import ActionSchema, CreateService, NatsBroker

async def greet_action(ctx):
    payload = ctx["payload"]
    return {"message": f"Hello {payload['name']}!"}

service = CreateService(version="1", name="greeter", workers=1)
service.add(actions=ActionSchema(name="greet", handle=greet_action))

broker = NatsBroker(servers="nats://localhost:4222")
await broker.connect()
await service.register(broker)
```

Clients can call your service with:

```python
response = await broker.call(
    topic="v1.greeter.greet",
    payload={"name": "world"},
)
```

Or publish a fire-and-forget event:

```python
await broker.publish(
    subject="v1.greeter.user_joined",
    payload={"user_id": "abc-123"},
)
```

## Microservice Integration Guide
1. **Model your actions**: Wrap each NATS subject in an `ActionSchema`.
   Provide a `validate` callable (e.g., Pydantic model) when you need
   structured payload validation.
2. **Compose services**: Use `CreateService` to group related actions
   and configure worker concurrency. Register the service with a shared
   broker instance per process.
3. **Share the broker**: Inject the connected `NatsBroker` into your
   dependency container (FastAPI dependency, Flask extension, task
   context, etc.) so both service handlers and outbound clients can
   reuse it.
4. **Graceful shutdown**: Await `broker.is_done` or listen for your
   runtime's shutdown signals to close connections cleanly.
5. **Structured logging**: Replace ad-hoc prints with the standard
   `logging` module to surface broker lifecycle events in production.

### Common Subject Pattern
The default subject format is `v{version}.{service}.{action}`. Use the
helper `prefix_topic` in `nats_client.utils` if you need to construct
subjects outside of the broker.

## FastAPI Example
```python
from fastapi import Depends, FastAPI

from nats_client import ActionSchema, CreateService, NatsBroker

app = FastAPI()
broker = NatsBroker(servers="nats://localhost:4222")
service = CreateService(version="1", name="greeter", workers=1)

async def greet_action(ctx):
    name = ctx["payload"]["name"]
    return {"message": f"Hello {name}!"}

service.add(actions=ActionSchema(name="greet", handle=greet_action))

@app.on_event("startup")
async def startup():
    await broker.connect()
    await service.register(broker)

@app.on_event("shutdown")
async def shutdown():
    if broker.nc is not None:
        await broker.nc.drain()

async def get_broker() -> NatsBroker:
    return broker

@app.post("/greet")
async def greet(payload: dict, broker: NatsBroker = Depends(get_broker)):
    reply = await broker.call("v1.greeter.greet", payload)
    return reply["result"]
```

### Running the Example
1. Start a local NATS server (see Docker command above).
2. Run the FastAPI app: `uvicorn app:app --reload`.
3. Send a request: `curl -X POST localhost:8000/greet -d '{"name":"Ada"}' -H 'Content-Type: application/json'`.

## Event Consumer Example
When you want a worker process to listen for subjects and react to
events, create a lightweight runner:

```python
# worker.py
import asyncio
from nats_client import ActionSchema, CreateService, NatsBroker


async def handle_order_created(ctx):
    order = ctx["payload"]
    print(f"Processing order {order['id']} for {order['customer']}")
    # perform business logic, persist to DB, etc.
    return {"ack": True}


async def main():
    broker = NatsBroker(servers="nats://localhost:4222")
    await broker.connect()

    service = CreateService(version="1", name="orders", workers=1)
    service.add(actions=ActionSchema(name="order_created", handle=handle_order_created))
    await service.register(broker)

    # Block until the broker signals shutdown (Ctrl+C or connection close)
    if broker.is_done is not None:
        await broker.is_done


if __name__ == "__main__":
    asyncio.run(main())
```

Publish an event from another component or REPL:

```python
import asyncio
from nats_client import NatsBroker


async def publish_event():
    broker = NatsBroker(servers="nats://localhost:4222")
    await broker.connect()
    await broker.publish(
        subject="v1.orders.order_created",
        payload={"id": "123", "customer": "Ada"},
        flush=True,
    )


asyncio.run(publish_event())
```

This pattern keeps the consumer process focused on subscription logic.
Scale horizontally by increasing `workers` or running multiple worker
processes; NATS queue groups ensure events are load-balanced when
`queue=True` on `ActionSchema`.

### Ad-hoc Subscribers
For situations where you need to attach a listener without defining a
full service, use `broker.subscribe` directly (assuming `broker` is an
already-connected `NatsBroker` instance):

```python
import asyncio
import logging
from nats_client import NatsBroker

logger = logging.getLogger(__name__)


async def log_event(ctx):
    data = ctx["payload"]
    logger.info("User %s logged in", data["user"])  # ctx also exposes ctx["msg"]


async def main() -> None:
    broker = NatsBroker(servers="nats://localhost:4222")
    await broker.connect()

    subscription = await broker.subscribe(
        subject="v1.audit.user_login",
        handler=log_event,
    )

    try:
        await asyncio.Event().wait()
    finally:
        await NatsBroker.unsubscribe(subscription)


asyncio.run(main())
```

## Django Integration Example
Create a reusable broker module, e.g. `myproject/nats_app/broker.py`:

```python
from nats_client import ActionSchema, CreateService, NatsBroker

broker = NatsBroker(servers="nats://localhost:4222")
service = CreateService(version="1", name="greeter")

async def greet_action(ctx):
    name = ctx["payload"]["name"]
    return {"message": f"Hello {name}!"}

service.add(actions=ActionSchema(name="greet", handle=greet_action))
```

Wire it into Django's startup lifecycle (`apps.py`):

```python
from django.apps import AppConfig
from django.conf import settings
from django.core.asgi import get_asgi_application
import asyncio

from .broker import broker, service


class NatsAppConfig(AppConfig):
    name = "myproject.nats_app"

    def ready(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._startup())

    async def _startup(self):
        await broker.connect()
        await service.register(broker)
```

Expose a view that uses the broker (`views.py`):

```python
from django.http import JsonResponse
from django.views import View

from .broker import broker


class GreetView(View):
    async def post(self, request):
        payload = await request.json()
        reply = await broker.call("v1.greeter.greet", payload)
        return JsonResponse(reply["result"])
```

Add an ASGI entry point (`asgi.py`) to enable async views:

```python
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
application = get_asgi_application()
```

### Running the Example
1. Ensure Django 4.2+ (ASGI support) and `uvicorn` are installed.
2. Start NATS (`docker run --rm -p 4222:4222 nats:2.10-alpine`).
3. Run the server: `uvicorn myproject.asgi:application --reload`.
4. Test the endpoint: `curl -X POST localhost:8000/greet -d '{"name":"Ada"}' -H 'Content-Type: application/json'`.

## Development Notes
- Install dev dependencies with `python -m pip install -e .[dev]` once
  optional extras are defined, or manually add tools (e.g., `black`,
  `isort`, `pytest`).
- Planning tasks live in `docs/TODO.md`.
- Add tests under `tests/` following the pytest conventions outlined in
  `AGENTS.md`.

Happy shipping!
