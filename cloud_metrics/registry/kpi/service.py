"""KPI Calculation Service — Milestone 13.

Explicit PUE / WUE / CUE methods. Not a generic formula engine.
Reportable calculations hard-block on incompatible units, missing inputs,
missing aggregation period/boundary, and zero IT energy.
Does not change orchestrator or ingestion behaviour.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional, Union

from sqlalchemy.orm import Session

from cloud_metrics.registry.evidence import EvidenceRegistryService
from cloud_metrics.registry.kpi.types import (
    APPROVED_STATUSES,
    CANDIDATE_STATUSES,
    DEFAULT_INPUT_NAMESPACES,
    KPI_CUE,
    KPI_PUE,
    KPI_WUE,
    KpiCalculationResult,
    KpiInput,
    NormalizedInput,
)
from cloud_metrics.registry.provenance import ProvenanceRegistryService
from cloud_metrics.registry.standards import StandardsRegistryService
from cloud_metrics.registry.unit import UnitRegistryService

logger = logging.getLogger(__name__)

_ENERGY_CANON = "kWh"
_WATER_CANON = "L"
_CARBON_CANON = "kgCO2e"

InputLike = Union[KpiInput, Mapping[str, Any]]


def _as_input(obj: InputLike, default_name: str) -> KpiInput:
    if isinstance(obj, KpiInput):
        if not obj.namespace:
            obj.namespace = DEFAULT_INPUT_NAMESPACES.get(obj.name or default_name)
        return obj
    data = dict(obj)
    name = data.get("name") or default_name
    return KpiInput(
        name=name,
        value=data.get("value"),
        unit=data.get("unit"),
        namespace=data.get("namespace") or DEFAULT_INPUT_NAMESPACES.get(name),
        metric_status=data.get("metric_status"),
        mapping_status=data.get("mapping_status"),
    )


class KpiCalculationService:
    """Controlled sustainability KPI calculator (PUE, WUE, CUE)."""

    def __init__(self, session: Optional[Session] = None) -> None:
        self._session = session
        self._units = UnitRegistryService(session=session)
        self._evidence = EvidenceRegistryService(session=session)
        self._standards = StandardsRegistryService(session=session)
        self._prov = ProvenanceRegistryService(session=session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_pue(
        self,
        facility_energy: InputLike,
        it_energy: InputLike,
        *,
        aggregation_period: Optional[str] = None,
        boundary: Optional[str] = None,
        reportable: bool = True,
        allow_candidate_inputs: bool = False,
        source: Optional[str] = None,
    ) -> KpiCalculationResult:
        """PUE = total facility energy / IT equipment energy (dimensionless)."""
        fac = _as_input(facility_energy, "total_facility_energy")
        ite = _as_input(it_energy, "it_equipment_energy")
        result = KpiCalculationResult(
            kpi_namespace=KPI_PUE,
            input_metrics=[fac.name, ite.name],
            input_values={fac.name: fac.value, ite.name: ite.value},
            aggregation_period=aggregation_period,
            boundary=boundary,
            formula="total_facility_energy / it_equipment_energy",
            unit="ratio",
        )
        n_fac = self._normalize(fac, "Energy", _ENERGY_CANON)
        n_it = self._normalize(ite, "Energy", _ENERGY_CANON)
        result.normalized_inputs = [n_fac, n_it]
        self._apply_common_gates(
            result,
            inputs=[fac, ite],
            normalized=[n_fac, n_it],
            denominator=n_it,
            denominator_label="IT equipment energy",
            reportable=reportable,
            allow_candidate_inputs=allow_candidate_inputs,
        )
        if result.calculation_status in {
            "missing_input",
            "invalid_unit",
            "blocked",
        }:
            return self._finalize(result, source=source)

        if n_fac.normalized_value is None or n_it.normalized_value is None:
            result.calculation_status = "missing_input"
            result.errors.append("Normalized energy values are missing")
            return self._finalize(result, source=source)

        result.value = float(n_fac.normalized_value) / float(n_it.normalized_value)
        if result.value < 1.0:
            result.warnings.append(
                f"PUE {result.value:.4f} is below 1.0; check facility vs IT boundary"
            )
        if result.calculation_status != "under_review":
            result.calculation_status = "calculated"
            result.validation_status = "valid"
            result.reportable_approved = True
        else:
            result.validation_status = "under_review"
            result.reportable_approved = False
        return self._finalize(result, source=source)

    def calculate_wue(
        self,
        water_usage: InputLike,
        it_energy: InputLike,
        *,
        aggregation_period: Optional[str] = None,
        boundary: Optional[str] = None,
        reportable: bool = True,
        allow_candidate_inputs: bool = False,
        source: Optional[str] = None,
    ) -> KpiCalculationResult:
        """WUE = water volume / IT energy (L/kWh after normalization)."""
        water = _as_input(water_usage, "water_usage_total")
        ite = _as_input(it_energy, "it_equipment_energy")
        result = KpiCalculationResult(
            kpi_namespace=KPI_WUE,
            input_metrics=[water.name, ite.name],
            input_values={water.name: water.value, ite.name: ite.value},
            aggregation_period=aggregation_period,
            boundary=boundary,
            formula="water_usage_total / it_equipment_energy",
            unit="L/kWh",
        )
        n_w = self._normalize(water, "WaterVolume", _WATER_CANON)
        n_it = self._normalize(ite, "Energy", _ENERGY_CANON)
        result.normalized_inputs = [n_w, n_it]
        self._apply_common_gates(
            result,
            inputs=[water, ite],
            normalized=[n_w, n_it],
            denominator=n_it,
            denominator_label="IT equipment energy",
            reportable=reportable,
            allow_candidate_inputs=allow_candidate_inputs,
        )
        if result.calculation_status in {
            "missing_input",
            "invalid_unit",
            "blocked",
        }:
            return self._finalize(result, source=source)

        if n_w.normalized_value is None or n_it.normalized_value is None:
            result.calculation_status = "missing_input"
            result.errors.append("Normalized WUE inputs are missing")
            return self._finalize(result, source=source)

        result.value = float(n_w.normalized_value) / float(n_it.normalized_value)
        if result.calculation_status != "under_review":
            result.calculation_status = "calculated"
            result.validation_status = "valid"
            result.reportable_approved = True
        else:
            result.validation_status = "under_review"
            result.reportable_approved = False
        return self._finalize(result, source=source)

    def calculate_cue(
        self,
        carbon: InputLike,
        it_energy: InputLike,
        *,
        aggregation_period: Optional[str] = None,
        boundary: Optional[str] = None,
        reportable: bool = True,
        allow_candidate_inputs: bool = False,
        source: Optional[str] = None,
        carbon_kind: str = "emission",
    ) -> KpiCalculationResult:
        """CUE = operational carbon / IT energy (kgCO2e/kWh).

        ``carbon_kind``:
          - ``emission`` (default): carbon is CarbonEmission (kgCO2e family)
          - ``intensity``: carbon is CarbonIntensity; multiplied by IT energy
            to obtain mass, then divided by IT energy (equals intensity in
            kgCO2e/kWh after conversion)
        """
        carb = _as_input(
            carbon,
            "carbon_intensity"
            if carbon_kind == "intensity"
            else "carbon_emission_operational",
        )
        ite = _as_input(it_energy, "it_equipment_energy")
        result = KpiCalculationResult(
            kpi_namespace=KPI_CUE,
            input_metrics=[carb.name, ite.name],
            input_values={carb.name: carb.value, ite.name: ite.value},
            aggregation_period=aggregation_period,
            boundary=boundary,
            formula=(
                "carbon_intensity * it_energy / it_energy"
                if carbon_kind == "intensity"
                else "carbon_emission_operational / it_equipment_energy"
            ),
            unit="kgCO2e/kWh",
        )
        n_it = self._normalize(ite, "Energy", _ENERGY_CANON)
        if carbon_kind == "intensity":
            n_c = self._normalize(carb, "CarbonIntensity", "gCO2e/kWh")
        else:
            n_c = self._normalize(carb, "CarbonEmission", _CARBON_CANON)
        result.normalized_inputs = [n_c, n_it]
        self._apply_common_gates(
            result,
            inputs=[carb, ite],
            normalized=[n_c, n_it],
            denominator=n_it,
            denominator_label="IT equipment energy",
            reportable=reportable,
            allow_candidate_inputs=allow_candidate_inputs,
        )
        if result.calculation_status in {
            "missing_input",
            "invalid_unit",
            "blocked",
        }:
            return self._finalize(result, source=source)

        if n_c.normalized_value is None or n_it.normalized_value is None:
            result.calculation_status = "missing_input"
            result.errors.append("Normalized CUE inputs are missing")
            return self._finalize(result, source=source)

        if carbon_kind == "intensity":
            # gCO2e/kWh -> kgCO2e/kWh
            result.value = float(n_c.normalized_value) / 1000.0
        else:
            result.value = float(n_c.normalized_value) / float(n_it.normalized_value)

        if result.calculation_status != "under_review":
            result.calculation_status = "calculated"
            result.validation_status = "valid"
            result.reportable_approved = True
        else:
            result.validation_status = "under_review"
            result.reportable_approved = False
        return self._finalize(result, source=source)

    def calculate(
        self,
        kpi: str,
        *,
        aggregation_period: Optional[str] = None,
        boundary: Optional[str] = None,
        reportable: bool = True,
        allow_candidate_inputs: bool = False,
        source: Optional[str] = None,
        **inputs: InputLike,
    ) -> KpiCalculationResult:
        """Dispatch by KPI name or namespace."""
        key = (kpi or "").strip().lower()
        common = dict(
            aggregation_period=aggregation_period,
            boundary=boundary,
            reportable=reportable,
            allow_candidate_inputs=allow_candidate_inputs,
            source=source,
        )
        if key in {"pue", KPI_PUE}:
            fac = inputs.get("total_facility_energy") or inputs.get("facility_energy")
            ite = inputs.get("it_equipment_energy") or inputs.get("it_energy")
            if fac is None or ite is None:
                raise ValueError("PUE requires total_facility_energy and it_equipment_energy")
            return self.calculate_pue(fac, ite, **common)
        if key in {"wue", KPI_WUE}:
            water = inputs.get("water_usage_total") or inputs.get("water_usage")
            ite = inputs.get("it_equipment_energy") or inputs.get("it_energy")
            if water is None or ite is None:
                raise ValueError("WUE requires water_usage_total and it_equipment_energy")
            return self.calculate_wue(water, ite, **common)
        if key in {"cue", KPI_CUE}:
            kind = (
                "intensity"
                if inputs.get("carbon_intensity")
                and not (
                    inputs.get("carbon_emission_operational") or inputs.get("carbon")
                )
                else "emission"
            )
            carbon = (
                inputs.get("carbon_emission_operational")
                or inputs.get("carbon")
                or inputs.get("carbon_intensity")
            )
            ite = inputs.get("it_equipment_energy") or inputs.get("it_energy")
            if carbon is None or ite is None:
                raise ValueError("CUE requires carbon input and it_equipment_energy")
            return self.calculate_cue(carbon, ite, carbon_kind=kind, **common)
        raise ValueError(f"Unsupported KPI '{kpi}'; expected pue, wue, or cue")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _normalize(
        self,
        inp: KpiInput,
        expected_kind: str,
        canonical_unit: str,
    ) -> NormalizedInput:
        uv = self._units.validate_observed_unit(
            observed_unit=inp.unit,
            expected_quantity_kind=expected_kind,
            canonical_unit=canonical_unit,
            metric_namespace=inp.namespace,
        )
        out = NormalizedInput(
            name=inp.name,
            original_value=inp.value,
            original_unit=inp.unit,
            quantity_kind=expected_kind,
            unit_validation_status=uv.validation_status,
            namespace=inp.namespace,
            message=uv.message,
            normalized_unit=canonical_unit,
        )
        if inp.value is None:
            return out
        if uv.validation_status not in {"valid", "normalized"}:
            return out
        src = uv.normalized_unit or inp.unit or canonical_unit
        try:
            if src == canonical_unit:
                out.normalized_value = float(inp.value)
            else:
                out.normalized_value = float(
                    self._units.convert_value(float(inp.value), src, canonical_unit)
                )
        except (ValueError, NotImplementedError) as exc:
            out.unit_validation_status = "incompatible"
            out.message = str(exc)
            out.normalized_value = None
        return out

    def _apply_common_gates(
        self,
        result: KpiCalculationResult,
        *,
        inputs: List[KpiInput],
        normalized: List[NormalizedInput],
        denominator: NormalizedInput,
        denominator_label: str,
        reportable: bool,
        allow_candidate_inputs: bool,
    ) -> None:
        missing = [n.name for n in normalized if n.original_value is None]
        if missing:
            result.calculation_status = "missing_input"
            result.validation_status = "missing_input"
            result.errors.append(f"Missing required input value(s): {', '.join(missing)}")
            return

        bad_units = [
            n
            for n in normalized
            if n.unit_validation_status
            not in {"valid", "normalized"}
        ]
        if bad_units:
            result.calculation_status = "invalid_unit"
            result.validation_status = "invalid_unit"
            for n in bad_units:
                msg = n.message or f"Invalid unit for {n.name}"
                result.errors.append(msg)
            return

        den = denominator.normalized_value
        if den is None or den == 0:
            result.calculation_status = "blocked"
            result.validation_status = "blocked"
            result.errors.append(
                f"{denominator_label} is zero or missing; cannot calculate KPI"
            )
            return
        if den < 0:
            result.calculation_status = "blocked"
            result.validation_status = "blocked"
            result.errors.append(f"{denominator_label} must be positive")
            return

        if reportable:
            if not (result.aggregation_period or "").strip():
                result.calculation_status = "blocked"
                result.validation_status = "blocked"
                result.errors.append(
                    "Aggregation period is required for a reportable KPI"
                )
                return
            if not (result.boundary or "").strip():
                result.calculation_status = "blocked"
                result.validation_status = "blocked"
                result.errors.append("Boundary is required for a reportable KPI")
                return

        if not allow_candidate_inputs and self._has_candidate_input(inputs):
            result.calculation_status = "under_review"
            result.validation_status = "under_review"
            result.warnings.append(
                "Candidate or under_review input cannot produce an approved "
                "reportable KPI"
            )
            result.reportable_approved = False

    def _has_candidate_input(self, inputs: List[KpiInput]) -> bool:
        for inp in inputs:
            statuses = [
                (inp.metric_status or "").lower(),
                (inp.mapping_status or "").lower(),
            ]
            ns_status = self._lookup_metric_status(inp.namespace)
            if ns_status:
                statuses.append(ns_status)
            for st in statuses:
                if st in CANDIDATE_STATUSES:
                    return True
        return False

    def _lookup_metric_status(self, namespace: Optional[str]) -> Optional[str]:
        if self._session is None or not namespace:
            return None
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        row = (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=namespace)
            .first()
        )
        return (row.status or "").lower() if row is not None else None

    def _lookup_metric_id(self, namespace: Optional[str]) -> Optional[int]:
        if self._session is None or not namespace:
            return None
        from cloud_metrics.models.cim_registry import CimMetricDefinition

        row = (
            self._session.query(CimMetricDefinition)
            .filter_by(namespace=namespace)
            .first()
        )
        return row.id if row is not None else None

    def _attach_enrichment(self, result: KpiCalculationResult) -> None:
        if not result.kpi_namespace:
            return
        ev = self._evidence.get_requirements_for_metric(result.kpi_namespace)
        result.evidence_requirements = list(ev.requirements)
        # Standards only for approved KPI definitions (seeded PUE exactMatch, etc.)
        kpi_status = self._lookup_metric_status(result.kpi_namespace)
        allow = kpi_status in APPROVED_STATUSES if kpi_status else True
        std = self._standards.get_mappings_for_metric(
            result.kpi_namespace,
            allow_approved=allow,
        )
        result.standards_mappings = list(std.mappings)

    def _record_provenance(
        self,
        result: KpiCalculationResult,
        *,
        source: Optional[str],
    ) -> None:
        if self._session is None:
            return
        try:
            entry = self._prov.record_activity(
                entity_type="kpi_calculation",
                entity_id=result.metric_definition_id,
                activity="kpi_calculation",
                agent="kpi_calculation_service",
                method="KpiCalculationService",
                inputs={
                    "kpi_namespace": result.kpi_namespace,
                    "input_values": result.input_values,
                    "normalized": [
                        {
                            "name": n.name,
                            "normalized_value": n.normalized_value,
                            "normalized_unit": n.normalized_unit,
                            "unit_status": n.unit_validation_status,
                        }
                        for n in result.normalized_inputs
                    ],
                    "aggregation_period": result.aggregation_period,
                    "boundary": result.boundary,
                    "source": source,
                },
                outputs={
                    "value": result.value,
                    "unit": result.unit,
                    "calculation_status": result.calculation_status,
                    "reportable_approved": result.reportable_approved,
                    "errors": list(result.errors),
                },
                notes=result.formula,
            )
            result.provenance_record_id = entry.id
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning("KPI provenance failed: %s", exc)
            result.warnings.append(f"provenance recording failed: {exc}")

    def _finalize(
        self,
        result: KpiCalculationResult,
        *,
        source: Optional[str],
    ) -> KpiCalculationResult:
        result.metric_definition_id = self._lookup_metric_id(result.kpi_namespace)
        self._attach_enrichment(result)
        if result.calculation_status == "calculated" and result.reportable_approved:
            result.validation_status = "valid"
        self._record_provenance(result, source=source)
        logger.info(
            "KPI %s status=%s value=%s approved=%s",
            result.kpi_namespace,
            result.calculation_status,
            result.value,
            result.reportable_approved,
        )
        return result


def get_kpi_calculation_service(
    session: Optional[Session] = None,
) -> KpiCalculationService:
    return KpiCalculationService(session=session)


CimKpiCalculationService = KpiCalculationService
SustainabilityKpiService = KpiCalculationService
