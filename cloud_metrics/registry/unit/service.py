"""Unit Registry service — CIM ``cim_units`` / ``cim_quantity_kinds`` (Milestone 5).

Without a SQLAlchemy session the service keeps the Milestone 1 skeleton contract
(``list_entries() == []``) so smoke tests remain stable. Legacy runtime
conversion in ``cloud_metrics.services.unit_registry_service`` is unchanged.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_metrics.registry.base import RegistryName, SKELETON_ONLY
from cloud_metrics.registry.unit.aliases import resolve_unit_alias
from cloud_metrics.registry.unit.types import (
    QuantityKindEntry,
    UnitEntry,
    UnitValidationResult,
)

logger = logging.getLogger(__name__)

# Quantity kinds that do not require an observed unit.
_UNITLESS_KINDS = frozenset({"Dimensionless", "Count"})


class UnitRegistryService:
    """Unit / Quantity Kind registry backed by ``cim_*`` tables when session set."""

    registry_name = RegistryName.UNIT
    skeleton_only = SKELETON_ONLY

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Skeleton-compatible surface
    # ------------------------------------------------------------------

    def list_entries(self) -> List[UnitEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimUnit

        return [self._to_unit_entry(u) for u in self._session.query(CimUnit).all()]

    def list_quantity_kinds(self) -> List[QuantityKindEntry]:
        if self._session is None:
            return []
        from cloud_metrics.models.cim_registry import CimQuantityKind

        return [
            self._to_qk_entry(q) for q in self._session.query(CimQuantityKind).all()
        ]

    def get_by_symbol(self, symbol: str) -> Optional[UnitEntry]:
        row = self._find_unit(symbol)
        return self._to_unit_entry(row) if row else None

    def get_by_alias(self, alias: str) -> Optional[UnitEntry]:
        resolved = resolve_unit_alias(alias)
        if resolved is None:
            return None
        return self.get_by_symbol(resolved)

    def get_quantity_kind(self, name: str) -> Optional[QuantityKindEntry]:
        if self._session is None or not name:
            return None
        from cloud_metrics.models.cim_registry import CimQuantityKind

        row = (
            self._session.query(CimQuantityKind)
            .filter(func.lower(CimQuantityKind.name) == name.strip().lower())
            .first()
        )
        return self._to_qk_entry(row) if row else None

    def get_canonical_unit(self, quantity_kind: str) -> Optional[UnitEntry]:
        if self._session is None or not quantity_kind:
            return None
        from cloud_metrics.models.cim_registry import CimQuantityKind, CimUnit

        qk = (
            self._session.query(CimQuantityKind)
            .filter(func.lower(CimQuantityKind.name) == quantity_kind.strip().lower())
            .first()
        )
        if qk is None:
            return None
        row = (
            self._session.query(CimUnit)
            .filter_by(quantity_kind_id=qk.id, canonical_unit_id=None)
            .first()
        )
        return self._to_unit_entry(row) if row else None

    def convert_value(self, value: float, from_unit: str, to_unit: str) -> float:
        if from_unit == to_unit:
            return value
        if self._session is None:
            raise NotImplementedError(
                "Unit conversion requires a DB session against cim_units."
            )
        src = self._find_unit(from_unit)
        dst = self._find_unit(to_unit)
        if src is None or dst is None:
            raise ValueError(f"Unit symbols not found: '{from_unit}' or '{to_unit}'")
        if src.quantity_kind_id != dst.quantity_kind_id:
            raise ValueError(
                f"Cannot convert between different quantity kinds: "
                f"{from_unit} → {to_unit}"
            )
        canon_val = value * float(src.conversion_factor) + float(src.conversion_offset)
        return (canon_val - float(dst.conversion_offset)) / float(dst.conversion_factor)

    # ------------------------------------------------------------------
    # Milestone 5: quantity-kind validation
    # ------------------------------------------------------------------

    def validate_observed_unit(
        self,
        *,
        observed_unit: Optional[str] = None,
        expected_quantity_kind: Optional[str] = None,
        canonical_unit: Optional[str] = None,
        metric_namespace: Optional[str] = None,
        unit_required: Optional[bool] = None,
    ) -> UnitValidationResult:
        """Validate ``observed_unit`` against an expected quantity kind.

        Does not raise; returns structured status for callers to attach as metadata.
        """
        result = UnitValidationResult(
            observed_unit=observed_unit,
            expected_quantity_kind=expected_quantity_kind,
            canonical_unit=canonical_unit,
            metric_namespace=metric_namespace,
        )

        if not expected_quantity_kind:
            result.validation_status = "not_required"
            result.severity = "info"
            result.message = "No expected quantity kind on metric definition"
            return result

        requires = (
            unit_required
            if unit_required is not None
            else expected_quantity_kind not in _UNITLESS_KINDS
        )

        # Missing observed unit
        token = resolve_unit_alias(observed_unit)
        if token is None:
            if not requires:
                result.validation_status = "valid"
                result.severity = "info"
                result.message = (
                    f"No unit provided; allowed for quantity kind "
                    f"{expected_quantity_kind}"
                )
                if not canonical_unit:
                    canon = self.get_canonical_unit(expected_quantity_kind)
                    result.canonical_unit = canon.symbol if canon else None
                return result
            result.validation_status = "missing"
            result.severity = "warning"
            result.message = (
                f"Missing unit for quantity kind {expected_quantity_kind}"
            )
            if not canonical_unit:
                canon = self.get_canonical_unit(expected_quantity_kind)
                result.canonical_unit = canon.symbol if canon else canonical_unit
            return result

        result.normalized_unit = token

        # Look up in registry (session optional — still classify unknown)
        entry = self.get_by_symbol(token) if self._session is not None else None
        if entry is None and self._session is not None:
            # Case-insensitive retry already in _find_unit; treat as unknown
            result.validation_status = "unknown"
            result.severity = "warning"
            result.message = f"Unknown unit '{observed_unit}' (normalized '{token}')"
            logger.info("unknown unit: observed=%s normalized=%s", observed_unit, token)
            return result

        if entry is None:
            # No session: cannot confirm; treat unresolved alias as unknown
            # unless token equals a well-known seeded symbol shape — still unknown
            result.validation_status = "unknown"
            result.severity = "warning"
            result.message = (
                f"Cannot verify unit '{token}' without Unit Registry session"
            )
            return result

        result.observed_quantity_kind = entry.quantity_kind
        result.normalized_unit = entry.symbol
        if not result.canonical_unit:
            result.canonical_unit = entry.canonical_unit_symbol or entry.symbol

        if entry.quantity_kind and entry.quantity_kind.lower() == expected_quantity_kind.lower():
            expected_canon = canonical_unit or entry.canonical_unit_symbol or entry.symbol
            if entry.symbol == expected_canon:
                result.validation_status = "valid"
                result.severity = "info"
                result.message = (
                    f"Unit '{entry.symbol}' matches quantity kind "
                    f"{expected_quantity_kind}"
                )
            else:
                result.validation_status = "normalized"
                result.severity = "info"
                result.message = (
                    f"Unit '{entry.symbol}' compatible with {expected_quantity_kind}; "
                    f"canonical is '{expected_canon}'"
                )
                result.canonical_unit = expected_canon
            logger.info(
                "unit validation %s: observed=%s qk=%s",
                result.validation_status,
                entry.symbol,
                expected_quantity_kind,
            )
            return result

        result.validation_status = "incompatible"
        result.severity = "error"
        result.message = (
            f"Unit '{entry.symbol}' is {entry.quantity_kind}, "
            f"expected {expected_quantity_kind}"
        )
        logger.info(
            "unit incompatible: observed=%s (%s) expected=%s",
            entry.symbol,
            entry.quantity_kind,
            expected_quantity_kind,
        )
        return result

    def validate_for_metric(
        self,
        metric_namespace: str,
        observed_unit: Optional[str] = None,
        *,
        unit_required: Optional[bool] = None,
    ) -> UnitValidationResult:
        """Load metric definition expectations then validate ``observed_unit``."""
        if self._session is None:
            return UnitValidationResult(
                observed_unit=observed_unit,
                metric_namespace=metric_namespace,
                validation_status="unknown",
                severity="warning",
                message="No session; cannot load metric quantity kind",
            )

        from cloud_metrics.models.cim_registry import CimMetricDefinition

        metric = (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=metric_namespace)
            .first()
        )
        if metric is None:
            return UnitValidationResult(
                observed_unit=observed_unit,
                metric_namespace=metric_namespace,
                validation_status="not_required",
                severity="info",
                message=f"Metric '{metric_namespace}' not found in Metric Registry",
            )

        qk_name = metric.quantity_kind.name if metric.quantity_kind else None
        canon = metric.canonical_unit.symbol if metric.canonical_unit else None
        return self.validate_observed_unit(
            observed_unit=observed_unit,
            expected_quantity_kind=qk_name,
            canonical_unit=canon,
            metric_namespace=metric_namespace,
            unit_required=unit_required,
        )

    def units_compatible(self, unit_symbol: str, quantity_kind_name: str) -> bool:
        """True when ``unit_symbol`` belongs to ``quantity_kind_name``."""
        result = self.validate_observed_unit(
            observed_unit=unit_symbol,
            expected_quantity_kind=quantity_kind_name,
        )
        return result.validation_status in {"valid", "normalized"}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _find_unit(self, symbol: Optional[str]):
        if self._session is None or not symbol:
            return None
        from cloud_metrics.models.cim_registry import CimUnit

        resolved = resolve_unit_alias(symbol) or symbol
        row = (
            self._session.query(CimUnit)
            .filter(func.lower(CimUnit.symbol) == resolved.lower())
            .first()
        )
        if row is not None:
            return row
        # Direct case-insensitive on original
        return (
            self._session.query(CimUnit)
            .filter(func.lower(CimUnit.symbol) == str(symbol).strip().lower())
            .first()
        )

    def _to_unit_entry(self, row) -> UnitEntry:
        qk = row.quantity_kind.name if row.quantity_kind is not None else None
        canon = None
        if row.canonical_unit is not None:
            canon = row.canonical_unit.symbol
        elif row.canonical_unit_id is None:
            canon = row.symbol
        return UnitEntry(
            id=row.id,
            symbol=row.symbol,
            name=row.name,
            quantity_kind=qk,
            si_base=bool(row.si_base),
            canonical_unit_symbol=canon,
            conversion_factor=float(row.conversion_factor or 1.0),
            conversion_offset=float(row.conversion_offset or 0.0),
            qudt_uri=row.qudt_uri,
            saref_uri=row.saref_uri,
            status=row.status,
        )

    def _to_qk_entry(self, row) -> QuantityKindEntry:
        return QuantityKindEntry(
            id=row.id,
            name=row.name,
            description=row.description,
            qudt_uri=row.qudt_uri,
            status=row.status,
        )


def get_unit_registry_service(
    session: Optional[Session] = None,
) -> UnitRegistryService:
    return UnitRegistryService(session=session)
