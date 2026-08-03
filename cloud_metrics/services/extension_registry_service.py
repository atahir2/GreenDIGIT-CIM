"""Extension Registry service placeholder (Milestone 1).

Delegates to the modular skeleton under ``cloud_metrics.registry.extension``.
No extension-metric handling is enforced yet.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.extension import (
    ExtensionEntry,
    ExtensionRegistryService,
    get_extension_registry_service,
)

__all__ = [
    "ExtensionEntry",
    "ExtensionRegistryService",
    "get_extension_registry_service",
    "list_extensions",
    "get_extension",
]


def list_extensions() -> List[ExtensionEntry]:
    return get_extension_registry_service().list_entries()


def get_extension(extension_id: int) -> Optional[ExtensionEntry]:
    return get_extension_registry_service().get_by_id(extension_id)
