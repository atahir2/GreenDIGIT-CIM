"""KPI Calculation Service — types (Milestone 13)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cloud_metrics.registry.evidence.types import EvidenceRequirementEntry
from cloud_metrics.registry.standards.types import StandardMappingEntry

# calculated | blocked | missing_input | invalid_unit | under_review
CalculationStatus = str

KPI_PUE = "cim:energy.efficiency.pue"
KPI_WUE = "cim:energy.efficiency.wue"
KPI_CUE = "cim:energy.efficiency.cue"

DEFAULT_INPUT_NAMESPACES: Dict[str, str] = {
    "total_facility_energy": "cim:facility.energy.consumption.total",
    "it_equipment_energy": "cim:facility.it.energy.consumption",
    "water_usage_total": "cim:water.usage.total",
    "carbon_emission_operational": "cim:carbon.emission.operational",
    "carbon_intensity": "cim:carbon.intensity.location_based",
}

CANDIDATE_STATUSES = frozenset(
    {"candidate", "draft", "pending", "under_review", "rejected"}
)
APPROVED_STATUSES = frozenset({"approved", "active"})


@dataclass
class KpiInput:
    """A single numeric input to a KPI calculation."""

    name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    namespace: Optional[str] = None
    metric_status: Optional[str] = None
    mapping_status: Optional[str] = None


@dataclass
class NormalizedInput:
    """Unit-validated, optionally converted input."""

    name: str
    original_value: Optional[float] = None
    original_unit: Optional[str] = None
    normalized_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    quantity_kind: Optional[str] = None
    unit_validation_status: Optional[str] = None
    namespace: Optional[str] = None
    message: Optional[str] = None


@dataclass
class KpiCalculationResult:
    """Outcome of a reportable KPI calculation (PUE / WUE / CUE)."""

    kpi_namespace: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    input_metrics: List[str] = field(default_factory=list)
    input_values: Dict[str, Any] = field(default_factory=dict)
    normalized_inputs: List[NormalizedInput] = field(default_factory=list)
    aggregation_period: Optional[str] = None
    boundary: Optional[str] = None
    validation_status: str = "pending"
    evidence_requirements: List[EvidenceRequirementEntry] = field(default_factory=list)
    standards_mappings: List[StandardMappingEntry] = field(default_factory=list)
    provenance_record_id: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    calculation_status: CalculationStatus = "pending"
    reportable_approved: bool = False
    formula: Optional[str] = None
    metric_definition_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_namespace": self.kpi_namespace,
            "value": self.value,
            "unit": self.unit,
            "input_metrics": list(self.input_metrics),
            "input_values": dict(self.input_values),
            "normalized_inputs": [
                {
                    "name": n.name,
                    "original_value": n.original_value,
                    "original_unit": n.original_unit,
                    "normalized_value": n.normalized_value,
                    "normalized_unit": n.normalized_unit,
                    "quantity_kind": n.quantity_kind,
                    "unit_validation_status": n.unit_validation_status,
                    "namespace": n.namespace,
                    "message": n.message,
                }
                for n in self.normalized_inputs
            ],
            "aggregation_period": self.aggregation_period,
            "boundary": self.boundary,
            "validation_status": self.validation_status,
            "evidence_requirements": [
                {
                    "standard_code": e.standard_code,
                    "evidence_type": e.evidence_type,
                    "requirement_level": e.requirement_level,
                    "description": e.description,
                    "boundary": e.boundary,
                    "reporting_period": e.reporting_period,
                }
                for e in self.evidence_requirements
            ],
            "standards_mappings": [
                {
                    "standard_code": m.standard_code,
                    "relation_type": m.relation_type,
                    "review_status": m.review_status,
                    "notes": m.notes,
                }
                for m in self.standards_mappings
            ],
            "provenance_record_id": self.provenance_record_id,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "calculation_status": self.calculation_status,
            "reportable_approved": self.reportable_approved,
            "formula": self.formula,
            "metric_definition_id": self.metric_definition_id,
        }
