"""Rule Registry — placeholder service (Milestone 1 skeleton).

Runtime validation currently lives in
``cloud_metrics.services.rule_registry_service``. Milestone 1 does not add
new rule behaviour.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.rule.types import RuleEntry


class RuleRegistryService:
    """Placeholder Rule Registry service."""

    registry_name = RegistryName.RULE
    skeleton_only = SKELETON_ONLY

    def list_entries(self) -> List[RuleEntry]:
        return []

    def get_by_name(self, name: str) -> Optional[RuleEntry]:
        return None

    def validate(self, payload: Dict[str, Any]) -> List[str]:
        """Skeleton stub — returns no violations."""
        return []


def get_rule_registry_service() -> RuleRegistryService:
    return RuleRegistryService()
