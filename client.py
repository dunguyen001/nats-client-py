"""Compatibility shim for legacy imports.

Historically the project exposed its runtime API from a top-level
``client`` module.  The implementation now lives under the ``src``
layout, but we re-export the public classes here to avoid breaking
downstream users who still import from ``client``.  The shim attempts to
import the packaged module first and falls back to adding the ``src``
directory to ``sys.path`` for in-place development usage.
"""

import sys
from importlib import import_module
from pathlib import Path


def _load_module():
    try:
        return import_module("nats_client.client")
    except ModuleNotFoundError:  # pragma: no cover - defensive path
        src_path = Path(__file__).resolve().parent / "src"
        if src_path.exists():
            sys.path.insert(0, str(src_path))
        return import_module("nats_client.client")


_client_module = _load_module()

ActionSchema = _client_module.ActionSchema
CreateService = _client_module.CreateService
NatsBroker = _client_module.NatsBroker

__all__ = ["ActionSchema", "CreateService", "NatsBroker"]
