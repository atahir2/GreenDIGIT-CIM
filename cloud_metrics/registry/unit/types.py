"""Unit Registry — base types (Milestone 1 skeleton)."""

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
    extra: Dict[str, Any] = field(default_factory=dict)
