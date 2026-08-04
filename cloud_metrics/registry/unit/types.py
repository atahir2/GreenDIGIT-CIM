"""Unit Registry — base types (Milestone 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class QuantityKindEntry:
    """Physical quantity kind (Energy, Power, Temperature, ...)."""

    name: str
    description: Optional[str] = None
    qudt_uri: Optional[str] = None
    id: Optional[int] = None
    status: str = "approved"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnitEntry:
    """Unit definition with optional conversion metadata."""

    symbol: str
    name: str
    quantity_kind: Optional[str] = None
    si_base: bool = False
    canonical_unit_symbol: Optional[str] = None
    conversion_factor: float = 1.0
    conversion_offset: float = 0.0
    qudt_uri: Optional[str] = None
    saref_uri: Optional[str] = None
    id: Optional[int] = None
    status: str = "approved"
    extra: Dict[str, Any] = field(default_factory=dict)


# valid | normalized | missing | incompatible | unknown | not_required
ValidationStatus = str
# info | warning | error
ValidationSeverity = str


@dataclass
class UnitValidationResult:
    """Outcome of comparing an observed unit to a metric's expected quantity kind."""

    observed_unit: Optional[str] = None
    canonical_unit: Optional[str] = None
    expected_quantity_kind: Optional[str] = None
    observed_quantity_kind: Optional[str] = None
    validation_status: ValidationStatus = "not_required"
    severity: ValidationSeverity = "info"
    message: Optional[str] = None
    normalized_unit: Optional[str] = None  # registry symbol after alias resolution
    metric_namespace: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.validation_status in {"valid", "normalized", "not_required"}
