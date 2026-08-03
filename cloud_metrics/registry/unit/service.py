"""Unit Registry — placeholder service (Milestone 1 skeleton).

A fuller implementation already exists at
``cloud_metrics.services.unit_registry_service``. This class defines the
intended modular interface without changing runtime behaviour.
"""

from __future__ import annotations

from typing import List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.unit.types import QuantityKindEntry, UnitEntry


class UnitRegistryService:
    """Placeholder Unit Registry service."""

    registry_name = RegistryName.UNIT
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[UnitEntry]:
        return []

    def list_quantity_kinds(self) -> List[QuantityKindEntry]:
        return []

    def get_by_symbol(self, symbol: str) -> Optional[UnitEntry]:
        return None

    def get_canonical_unit(self, quantity_kind: str) -> Optional[UnitEntry]:
        return None

    def convert_value(
        self, value: float, from_unit: str, to_unit: str
    ) -> float:
        """Skeleton stub — use services.unit_registry_service at runtime today."""
        if from_unit == to_unit:
            return value
        raise NotImplementedError(
            "Unit conversion is not implemented in the Milestone 1 skeleton. "
            "Use cloud_metrics.services.unit_registry_service.convert_value."
        )


def get_unit_registry_service() -> UnitRegistryService:
    return UnitRegistryService()
