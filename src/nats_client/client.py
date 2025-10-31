"""Facade preserving the legacy module path ``nats_client.client``.

The implementation has been modularised across ``broker``, ``schema``,
and ``service`` submodules.  Importing from this module continues to
work for downstream projects that still rely on the historical layout.
"""

from .broker import NatsBroker
from .schema import ActionSchema
from .service import CreateService

__all__ = ["ActionSchema", "CreateService", "NatsBroker"]
