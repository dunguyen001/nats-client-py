"""Public package interface for :mod:`nats_client`.

The package exposes the broker helper classes and supporting utilities
via a stable top-level API.
"""

from .broker import NatsBroker
from .schema import ActionSchema
from .service import CreateService

__all__ = ["ActionSchema", "CreateService", "NatsBroker"]
