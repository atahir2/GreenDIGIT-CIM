"""Static seed catalogues for Milestone 3 registry bootstrap.

These definitions are loaded into additive ``cim_*`` tables only.
They do not touch legacy tables or the ingestion pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Controlled vocabularies (no dedicated DB table for relation types)
# ---------------------------------------------------------------------------

RELATION_TYPES: Tuple[str, ...] = (
    "exactMatch",
    "closeMatch",
    "broadMatch",
    "narrowMatch",
    "inputToKPI",
    "derivedFrom",
    "contextualMatch",
    "extensionMetric",
    "noMatch",
    "underReview",
)

SEED_SOURCE = {
    "name": "cim_registry_bootstrap",
    "type": "manual",
    "protocol": "internal",
    "format": "seed",
    "schema_version": "m3",
    "auth_method": "none",
    "status": "approved",
    "review_status": "approved",
    "notes": "Synthetic source used for bootstrap standards↔metric mappings.",
}

CREATED_BY = "milestone3_seed"

# ---------------------------------------------------------------------------
# Quantity kinds & units
# ---------------------------------------------------------------------------

QUANTITY_KINDS: List[Dict[str, Any]] = [
    {
        "name": "Power",
        "description": "Electric power / rate of energy transfer",
        "qudt_uri": "http://qudt.org/vocab/quantitykind/Power",
    },
    {
        "name": "Energy",
        "description": "Energy consumption or work",
        "qudt_uri": "http://qudt.org/vocab/quantitykind/Energy",
    },
    {
        "name": "CarbonEmission",
        "description": "Greenhouse gas emissions as CO2 equivalent",
        "qudt_uri": None,
    },
    {
        "name": "CarbonIntensity",
        "description": "Emissions intensity relative to energy",
        "qudt_uri": None,
    },
    {
        "name": "Time",
        "description": "Duration or elapsed time",
        "qudt_uri": "http://qudt.org/vocab/quantitykind/Time",
    },
    {
        "name": "DataSize",
        "description": "Digital information size",
        "qudt_uri": "http://qudt.org/vocab/quantitykind/InformationEntropy",
    },
    {
        "name": "Ratio",
        "description": "Ratio or percentage quantity",
        "qudt_uri": "http://qudt.org/vocab/quantitykind/DimensionlessRatio",
    },
    {
        "name": "Dimensionless",
        "description": "Dimensionless score or factor",
        "qudt_uri": "http://qudt.org/vocab/quantitykind/Dimensionless",
    },
    {
        "name": "WaterVolume",
        "description": "Volume of water",
        "qudt_uri": "http://qudt.org/vocab/quantitykind/Volume",
    },
    {
        "name": "Count",
        "description": "Discrete countable quantity",
        "qudt_uri": "http://qudt.org/vocab/quantitykind/Dimensionless",
    },
]

# symbol: (name, quantity_kind, si_base, canonical_symbol, factor_to_canonical, offset)
UNITS: Dict[str, Tuple[Any, ...]] = {
    # Power (canonical W)
    "W": ("watt", "Power", True, "W", 1.0, 0.0),
    "kW": ("kilowatt", "Power", False, "W", 1000.0, 0.0),
    # Energy (canonical kWh)
    "Wh": ("watt-hour", "Energy", False, "kWh", 0.001, 0.0),
    "kWh": ("kilowatt-hour", "Energy", False, "kWh", 1.0, 0.0),
    "J": ("joule", "Energy", True, "kWh", 2.777777777777778e-7, 0.0),
    # Carbon emission (canonical kgCO2e)
    "kgCO2e": ("kilogram CO2 equivalent", "CarbonEmission", False, "kgCO2e", 1.0, 0.0),
    "gCO2e": ("gram CO2 equivalent", "CarbonEmission", False, "kgCO2e", 0.001, 0.0),
    # Carbon intensity (canonical gCO2e/kWh)
    "gCO2e/kWh": (
        "grams CO2e per kilowatt-hour",
        "CarbonIntensity",
        False,
        "gCO2e/kWh",
        1.0,
        0.0,
    ),
    # Time (canonical s)
    "s": ("second", "Time", True, "s", 1.0, 0.0),
    "ms": ("millisecond", "Time", False, "s", 0.001, 0.0),
    "h": ("hour", "Time", False, "s", 3600.0, 0.0),
    # DataSize (canonical B)
    "B": ("byte", "DataSize", True, "B", 1.0, 0.0),
    "KB": ("kilobyte", "DataSize", False, "B", 1024.0, 0.0),
    "MB": ("megabyte", "DataSize", False, "B", 1024.0**2, 0.0),
    "GB": ("gigabyte", "DataSize", False, "B", 1024.0**3, 0.0),
    "TB": ("terabyte", "DataSize", False, "B", 1024.0**4, 0.0),
    # Ratio (canonical %)
    "%": ("percent", "Ratio", False, "%", 1.0, 0.0),
    "ratio": ("dimensionless ratio (0-1)", "Ratio", False, "%", 100.0, 0.0),
    # Dimensionless (canonical dimensionless)
    "score": ("score", "Dimensionless", False, "dimensionless", 1.0, 0.0),
    "dimensionless": ("dimensionless", "Dimensionless", True, "dimensionless", 1.0, 0.0),
    # Water (canonical L)
    "L": ("litre", "WaterVolume", False, "L", 1.0, 0.0),
    "m3": ("cubic metre", "WaterVolume", False, "L", 1000.0, 0.0),
    # Count
    "count": ("count", "Count", True, "count", 1.0, 0.0),
}

# ---------------------------------------------------------------------------
# Lifecycle stages
# ---------------------------------------------------------------------------

LIFECYCLE_STAGES: List[Dict[str, Any]] = [
    {"stage_key": "planning", "name": "Planning", "sequence": 1,
     "label": "Planning", "description": "RI / facility planning stage"},
    {"stage_key": "design", "name": "Design", "sequence": 2,
     "label": "Design", "description": "Architecture and design stage"},
    {"stage_key": "procurement", "name": "Procurement", "sequence": 3,
     "label": "Procurement", "description": "Equipment and service procurement"},
    {"stage_key": "deployment", "name": "Deployment", "sequence": 4,
     "label": "Deployment", "description": "Installation and commissioning"},
    {"stage_key": "operation", "name": "Operation", "sequence": 5,
     "label": "Operation", "description": "Steady-state operation"},
    {"stage_key": "optimisation", "name": "Optimisation", "sequence": 6,
     "label": "Optimisation", "description": "Efficiency and tuning"},
    {"stage_key": "reproducibility", "name": "Reproducibility", "sequence": 7,
     "label": "Reproducibility", "description": "Experiment / workflow reproducibility"},
    {"stage_key": "reporting", "name": "Reporting", "sequence": 8,
     "label": "Reporting", "description": "Disclosure and KPI reporting"},
    {"stage_key": "continuous_improvement", "name": "Continuous Improvement", "sequence": 9,
     "label": "Continuous Improvement", "description": "Ongoing improvement cycle"},
    {"stage_key": "decommissioning", "name": "Decommissioning", "sequence": 10,
     "label": "Decommissioning", "description": "End-of-life and retirement"},
]

# ---------------------------------------------------------------------------
# Standards
# ---------------------------------------------------------------------------

STANDARDS: List[Dict[str, Any]] = [
    {"code": "QUDT", "name": "Quantities, Units, Dimensions and Types",
     "standard_version": "2.1", "vocabulary_type": "ontology", "domain": "units",
     "namespace_prefix": "qudt", "namespace_uri": "http://qudt.org/schema/qudt/",
     "description": "Vocabulary for quantities, units, and dimensions."},
    {"code": "SOSA-SSN", "name": "SOSA/SSN",
     "standard_version": "1.0", "vocabulary_type": "ontology", "domain": "observations",
     "namespace_prefix": "sosa", "namespace_uri": "http://www.w3.org/ns/sosa/",
     "description": "Sensor, Observation, Sample, and Actuator / Semantic Sensor Network."},
    {"code": "SAREF", "name": "Smart Applications REFerence ontology",
     "standard_version": "3.1", "vocabulary_type": "ontology", "domain": "iot",
     "namespace_prefix": "saref", "namespace_uri": "https://saref.etsi.org/core/",
     "description": "ETSI ontology for smart applications and energy-related devices."},
    {"code": "SCHEMA-ORG", "name": "schema.org",
     "standard_version": "latest", "vocabulary_type": "vocabulary", "domain": "web",
     "namespace_prefix": "schema", "namespace_uri": "https://schema.org/",
     "description": "General-purpose structured data vocabulary."},
    {"code": "PROV-O", "name": "PROV Ontology",
     "standard_version": "1.0", "vocabulary_type": "ontology", "domain": "provenance",
     "namespace_prefix": "prov", "namespace_uri": "http://www.w3.org/ns/prov#",
     "description": "W3C provenance ontology."},
    {"code": "DCAT", "name": "Data Catalog Vocabulary",
     "standard_version": "2", "vocabulary_type": "vocabulary", "domain": "data",
     "namespace_prefix": "dcat", "namespace_uri": "http://www.w3.org/ns/dcat#",
     "description": "W3C vocabulary for data catalogues."},
    {"code": "RO-CRATE", "name": "Research Object Crate",
     "standard_version": "1.1", "vocabulary_type": "convention", "domain": "research",
     "namespace_prefix": "ro-crate", "namespace_uri": "https://w3id.org/ro/crate/",
     "description": "Packaging convention for research objects and workflows."},
    {"code": "OTEL", "name": "OpenTelemetry",
     "standard_version": "1.x", "vocabulary_type": "convention", "domain": "observability",
     "namespace_prefix": "otel", "namespace_uri": "https://opentelemetry.io/",
     "description": "Observability framework and semantic conventions."},
    {"code": "ISO-IEC-30134", "name": "ISO/IEC 30134 Data centre KPIs",
     "standard_version": "series", "vocabulary_type": "standard", "domain": "datacentre",
     "namespace_prefix": "iso30134", "namespace_uri": None,
     "description": "International KPIs for data centre resource efficiency (PUE, WUE, CUE, …)."},
    {"code": "EN-50600", "name": "EN 50600 Data centre facilities and infrastructures",
     "standard_version": "series", "vocabulary_type": "standard", "domain": "datacentre",
     "namespace_prefix": "en50600", "namespace_uri": None,
     "description": "European standard series for data centre design and operation."},
    {"code": "OCP", "name": "Open Compute Project",
     "standard_version": "latest", "vocabulary_type": "convention", "domain": "hardware",
     "namespace_prefix": "ocp", "namespace_uri": "https://www.opencompute.org/",
     "description": "Open hardware and efficiency practices for compute infrastructure."},
    {"code": "ISO-14040-14044", "name": "ISO 14040/14044 Life Cycle Assessment",
     "standard_version": "2006", "vocabulary_type": "standard", "domain": "environment",
     "namespace_prefix": "iso14040", "namespace_uri": None,
     "description": "Principles and requirements for life cycle assessment."},
    {"code": "ISO-50001", "name": "ISO 50001 Energy management systems",
     "standard_version": "2018", "vocabulary_type": "standard", "domain": "energy",
     "namespace_prefix": "iso50001", "namespace_uri": None,
     "description": "Requirements for energy management systems."},
    {"code": "ISO-14001", "name": "ISO 14001 Environmental management systems",
     "standard_version": "2015", "vocabulary_type": "standard", "domain": "environment",
     "namespace_prefix": "iso14001", "namespace_uri": None,
     "description": "Requirements for environmental management systems."},
    {"code": "EU-COC-DC", "name": "EU Code of Conduct for Data Centres",
     "standard_version": "2025", "vocabulary_type": "standard", "domain": "datacentre",
     "namespace_prefix": "eu-coc", "namespace_uri": None,
     "description": "EU best-practice guidelines for data centre energy efficiency."},
]

# ---------------------------------------------------------------------------
# Metrics
# namespace, label, description, domain, category, subcategory,
# quantity_kind, canonical_unit, metric_type, notes
# ---------------------------------------------------------------------------

METRICS: List[Dict[str, Any]] = [
    # Energy and power
    dict(namespace="cim:energy.power.total", label="Total power",
         description="Aggregate instantaneous or average power draw.",
         domain="energy", category="energy", subcategory="power",
         quantity_kind="Power", canonical_unit="W", metric_type="observed",
         notes="Facility- or scope-level total power."),
    dict(namespace="cim:energy.consumption.total", label="Total energy consumption",
         description="Aggregate energy consumed over a period.",
         domain="energy", category="energy", subcategory="consumption",
         quantity_kind="Energy", canonical_unit="kWh", metric_type="observed"),
    dict(namespace="cim:compute.node.power.draw", label="Compute node power draw",
         description="Power drawn by a compute node.",
         domain="energy", category="compute", subcategory="power",
         quantity_kind="Power", canonical_unit="W", metric_type="observed"),
    dict(namespace="cim:compute.gpu.power.average", label="GPU average power",
         description="Average GPU power over a sampling window.",
         domain="energy", category="compute", subcategory="gpu",
         quantity_kind="Power", canonical_unit="W", metric_type="observed"),
    dict(namespace="cim:facility.energy.consumption.total", label="Facility total energy",
         description="Total facility energy consumption (PUE numerator input).",
         domain="energy", category="facility", subcategory="consumption",
         quantity_kind="Energy", canonical_unit="kWh", metric_type="observed"),
    dict(namespace="cim:facility.it.energy.consumption", label="IT equipment energy",
         description="IT equipment energy consumption (PUE denominator input).",
         domain="energy", category="facility", subcategory="it_energy",
         quantity_kind="Energy", canonical_unit="kWh", metric_type="observed"),
    # Compute / infrastructure
    dict(namespace="cim:compute.cpu.utilisation", label="CPU utilisation",
         description="CPU utilisation as a percentage of capacity.",
         domain="performance", category="compute", subcategory="cpu",
         quantity_kind="Ratio", canonical_unit="%", metric_type="observed"),
    dict(namespace="cim:compute.memory.usage", label="Memory usage",
         description="Memory used by a compute resource.",
         domain="performance", category="compute", subcategory="memory",
         quantity_kind="DataSize", canonical_unit="B", metric_type="observed"),
    dict(namespace="cim:storage.capacity.used", label="Storage capacity used",
         description="Used storage capacity.",
         domain="storage", category="storage", subcategory="capacity",
         quantity_kind="DataSize", canonical_unit="B", metric_type="observed"),
    dict(namespace="cim:network.traffic.ingress", label="Network ingress traffic",
         description="Inbound network traffic volume.",
         domain="network", category="network", subcategory="traffic",
         quantity_kind="DataSize", canonical_unit="B", metric_type="observed"),
    dict(namespace="cim:network.traffic.egress", label="Network egress traffic",
         description="Outbound network traffic volume.",
         domain="network", category="network", subcategory="traffic",
         quantity_kind="DataSize", canonical_unit="B", metric_type="observed"),
    # Carbon
    dict(namespace="cim:carbon.emission.operational", label="Operational carbon emission",
         description="Operational GHG emissions as CO2 equivalent.",
         domain="environment", category="carbon", subcategory="emission",
         quantity_kind="CarbonEmission", canonical_unit="kgCO2e", metric_type="calculated"),
    dict(namespace="cim:carbon.intensity.location_based", label="Location-based carbon intensity",
         description="Grid / location-based carbon intensity of electricity.",
         domain="environment", category="carbon", subcategory="intensity",
         quantity_kind="CarbonIntensity", canonical_unit="gCO2e/kWh", metric_type="observed",
         notes="Contextual alignment to carbon reporting; not claimed as exactMatch to a specific ISO clause."),
    # Water
    dict(namespace="cim:water.usage.total", label="Total water usage",
         description="Total water used by the site or facility.",
         domain="environment", category="water", subcategory="usage",
         quantity_kind="WaterVolume", canonical_unit="L", metric_type="observed"),
    # Workflow
    dict(namespace="cim:workflow.execution.duration", label="Workflow execution duration",
         description="Wall-clock duration of a workflow run.",
         domain="performance", category="workflow", subcategory="execution",
         quantity_kind="Time", canonical_unit="s", metric_type="observed"),
    dict(namespace="cim:workflow.energy.per_run", label="Workflow energy per run",
         description="Energy attributed to a single workflow run.",
         domain="energy", category="workflow", subcategory="energy",
         quantity_kind="Energy", canonical_unit="kWh", metric_type="calculated"),
    dict(namespace="cim:workflow.carbon.per_run", label="Workflow carbon per run",
         description="Carbon emissions attributed to a single workflow run.",
         domain="environment", category="workflow", subcategory="carbon",
         quantity_kind="CarbonEmission", canonical_unit="kgCO2e", metric_type="calculated"),
    # KPIs
    dict(namespace="cim:energy.efficiency.pue", label="Power Usage Effectiveness",
         description="Facility energy / IT energy (ISO/IEC 30134-2).",
         domain="energy", category="efficiency", subcategory="pue",
         quantity_kind="Ratio", canonical_unit="ratio", metric_type="calculated_kpi",
         notes="Reportable KPI; requires aggregation period and boundary."),
    dict(namespace="cim:energy.efficiency.wue", label="Water Usage Effectiveness",
         description="Water use effectiveness KPI for data centres.",
         domain="environment", category="efficiency", subcategory="wue",
         quantity_kind="Ratio", canonical_unit="ratio", metric_type="calculated_kpi"),
    dict(namespace="cim:energy.efficiency.cue", label="Carbon Usage Effectiveness",
         description="Carbon usage effectiveness KPI for data centres.",
         domain="environment", category="efficiency", subcategory="cue",
         quantity_kind="Ratio", canonical_unit="ratio", metric_type="calculated_kpi"),
]

# metric_namespace -> list of (stage_key, relevance)
METRIC_LIFECYCLE_LINKS: Dict[str, List[Tuple[str, str]]] = {
    "cim:compute.node.power.draw": [
        ("operation", "primary"),
        ("optimisation", "secondary"),
        ("reproducibility", "secondary"),
        ("reporting", "conditional"),
    ],
    "cim:compute.gpu.power.average": [
        ("operation", "primary"),
        ("optimisation", "secondary"),
        ("reproducibility", "secondary"),
        ("reporting", "conditional"),
    ],
    "cim:workflow.energy.per_run": [
        ("operation", "primary"),
        ("reproducibility", "primary"),
        ("reporting", "secondary"),
    ],
    "cim:energy.efficiency.pue": [
        ("operation", "primary"),
        ("reporting", "primary"),
        ("continuous_improvement", "secondary"),
    ],
    "cim:carbon.emission.operational": [
        ("operation", "primary"),
        ("reporting", "primary"),
    ],
    "cim:water.usage.total": [
        ("operation", "primary"),
        ("reporting", "primary"),
    ],
}

# Safe standards mappings:
# (metric_namespace, standard_code, relation_type, source_key_suffix, rationale)
STANDARD_MAPPINGS: List[Tuple[str, str, str, str, str]] = [
    (
        "cim:energy.efficiency.pue",
        "ISO-IEC-30134",
        "exactMatch",
        "pue",
        "PUE is defined in ISO/IEC 30134-2.",
    ),
    (
        "cim:energy.efficiency.pue",
        "EN-50600",
        "exactMatch",
        "pue",
        "EN 50600 aligns with data-centre PUE reporting practices.",
    ),
    (
        "cim:compute.node.power.draw",
        "QUDT",
        "contextualMatch",
        "power",
        "Quantity/unit alignment to QUDT Power/Watt concepts; not a full metric identity claim.",
    ),
    (
        "cim:compute.node.power.draw",
        "SOSA-SSN",
        "contextualMatch",
        "observation",
        "Fits SOSA Observation model for measured power values.",
    ),
    (
        "cim:compute.node.power.draw",
        "SAREF",
        "closeMatch",
        "power",
        "Close conceptual match to SAREF power-related device measurements.",
    ),
    (
        "cim:compute.node.power.draw",
        "ISO-IEC-30134",
        "inputToKPI",
        "power-input",
        "Node power can feed facility/IT energy KPIs; not itself a 30134 KPI.",
    ),
    (
        "cim:compute.node.power.draw",
        "EN-50600",
        "inputToKPI",
        "power-input",
        "May contribute as an input measurement toward EN 50600 energy assessments.",
    ),
    (
        "cim:compute.gpu.power.average",
        "QUDT",
        "contextualMatch",
        "gpu-power",
        "Quantity/unit alignment to QUDT Power/Watt concepts; not a full metric identity claim.",
    ),
    (
        "cim:compute.gpu.power.average",
        "SOSA-SSN",
        "contextualMatch",
        "gpu-observation",
        "Fits SOSA Observation model for measured GPU power values.",
    ),
    (
        "cim:compute.gpu.power.average",
        "SAREF",
        "closeMatch",
        "gpu-power",
        "Close conceptual match to SAREF power-related device measurements.",
    ),
    (
        "cim:compute.gpu.power.average",
        "OCP",
        "contextualMatch",
        "gpu-ocp",
        "Contextual to Open Compute Project efficiency / hardware telemetry practices.",
    ),
    (
        "cim:workflow.energy.per_run",
        "QUDT",
        "contextualMatch",
        "energy",
        "Unit/quantity alignment to QUDT Energy concepts.",
    ),
    (
        "cim:workflow.energy.per_run",
        "PROV-O",
        "contextualMatch",
        "provenance",
        "Workflow energy attribution benefits from PROV-O activity/entity modelling.",
    ),
    (
        "cim:workflow.energy.per_run",
        "RO-CRATE",
        "contextualMatch",
        "ro-crate",
        "Relevant for packaging reproducible workflow energy results; not an exact metric match.",
    ),
    (
        "cim:workflow.energy.per_run",
        "SCHEMA-ORG",
        "contextualMatch",
        "schema",
        "Reproducibility / Dataset metadata relevance via schema.org; not exact.",
    ),
    (
        "cim:carbon.emission.operational",
        "ISO-14040-14044",
        "contextualMatch",
        "carbon-op",
        "Contextual to LCA / GHG inventory concepts; not claimed as exactMatch to a specific clause.",
    ),
    (
        "cim:carbon.emission.operational",
        "EU-COC-DC",
        "contextualMatch",
        "carbon-op-coc",
        "Contextual to data-centre carbon reporting practices under EU CoC guidance.",
    ),
    (
        "cim:carbon.intensity.location_based",
        "ISO-14040-14044",
        "contextualMatch",
        "carbon-intensity",
        "Contextual to LCA / GHG inventory concepts; not claimed as exactMatch to a specific clause.",
    ),
    (
        "cim:carbon.intensity.location_based",
        "EU-COC-DC",
        "contextualMatch",
        "carbon-intensity",
        "Relevant to data-centre carbon reporting practices under EU CoC guidance.",
    ),
    (
        "cim:water.usage.total",
        "ISO-IEC-30134",
        "inputToKPI",
        "water-wue-input",
        "Facility water usage can feed WUE (ISO/IEC 30134-9); not itself the WUE KPI.",
    ),
    (
        "cim:water.usage.total",
        "EN-50600",
        "contextualMatch",
        "water-en",
        "Contextual to EN 50600 water / environmental reporting practices.",
    ),
]

# ---------------------------------------------------------------------------
# Validation rules
# ---------------------------------------------------------------------------

VALIDATION_RULES: List[Dict[str, Any]] = [
    {
        "name": "metric_requires_namespace",
        "description": "Every metric must have a namespace",
        "rule_type": "required_field",
        "target_registry": "metric",
        "condition": {"field": "namespace", "op": "required"},
        "severity": "error",
    },
    {
        "name": "numeric_metric_requires_unit",
        "description": "Every numeric metric must have a unit unless explicitly dimensionless",
        "rule_type": "required_field",
        "target_registry": "metric",
        "condition": {
            "field": "canonical_unit_id",
            "op": "required_unless",
            "unless_quantity_kind": ["Dimensionless"],
        },
        "severity": "error",
    },
    {
        "name": "observed_metric_requires_timestamp_and_source",
        "description": "Every observed metric must have timestamp and source",
        "rule_type": "required_field",
        "target_registry": "metric",
        "condition": {
            "when_metric_type": "observed",
            "require": ["timestamp", "source"],
        },
        "severity": "error",
    },
    {
        "name": "calculated_metric_requires_derivation",
        "description": "Every calculated metric must have formula or derivation method",
        "rule_type": "required_field",
        "target_registry": "metric",
        "condition": {
            "when_metric_type": ["calculated", "calculated_kpi", "derived"],
            "require": ["formula_or_derivation_method"],
        },
        "severity": "warning",
    },
    {
        "name": "energy_distinguishes_power_vs_energy",
        "description": "Every energy metric must distinguish power from energy",
        "rule_type": "cross_field",
        "target_registry": "metric",
        "condition": {
            "domain": "energy",
            "quantity_kind_in": ["Power", "Energy"],
            "unit_must_match_quantity_kind": True,
        },
        "severity": "error",
    },
    {
        "name": "kpi_requires_period_and_boundary",
        "description": "Every reportable KPI must have aggregation period and boundary",
        "rule_type": "required_field",
        "target_registry": "metric",
        "condition": {
            "when_metric_type": "calculated_kpi",
            "require": ["aggregation_period", "boundary"],
        },
        "severity": "warning",
    },
    {
        "name": "workflow_reproducibility_requires_run_context",
        "description": "Workflow metrics for reproducibility must include workflow/run context",
        "rule_type": "required_field",
        "target_registry": "metric",
        "condition": {
            "when_category": "workflow",
            "when_lifecycle_stage": "reproducibility",
            "require": ["workflow_id", "run_id"],
        },
        "severity": "warning",
    },
    {
        "name": "extension_metric_requires_justification",
        "description": "Every extension metric must include justification and review status",
        "rule_type": "required_field",
        "target_registry": "extension",
        "condition": {"require": ["justification", "review_status"]},
        "severity": "error",
    },
]

# ---------------------------------------------------------------------------
# Evidence requirements
# (metric_namespace, standard_code, evidence_type, requirement_level,
#  reporting_period, aggregation_method, boundary, description)
# ---------------------------------------------------------------------------

EVIDENCE_REQUIREMENTS: List[Dict[str, Any]] = [
    {
        "metric_namespace": "cim:energy.efficiency.pue",
        "standard_code": "ISO-IEC-30134",
        "evidence_type": "calculation",
        "requirement_level": "mandatory",
        "reporting_period": "monthly_or_annual",
        "aggregation_method": "ratio",
        "boundary": "facility",
        "description": (
            "PUE requires total facility energy, IT equipment energy, "
            "aggregation period, calculation boundary, and metering source."
        ),
    },
    {
        "metric_namespace": "cim:energy.efficiency.pue",
        "standard_code": "ISO-IEC-30134",
        "evidence_type": "measurement",
        "requirement_level": "mandatory",
        "reporting_period": "continuous_or_interval",
        "aggregation_method": "sum",
        "boundary": "facility_and_it",
        "description": "Metered facility and IT energy inputs for PUE.",
    },
    {
        "metric_namespace": "cim:energy.efficiency.wue",
        "standard_code": "ISO-IEC-30134",
        "evidence_type": "measurement",
        "requirement_level": "mandatory",
        "reporting_period": "monthly_or_annual",
        "aggregation_method": "sum",
        "boundary": "site_or_facility",
        "description": (
            "WUE requires water use, aggregation period, site/facility boundary, and source."
        ),
    },
    {
        "metric_namespace": "cim:energy.efficiency.cue",
        "standard_code": "ISO-IEC-30134",
        "evidence_type": "calculation",
        "requirement_level": "mandatory",
        "reporting_period": "monthly_or_annual",
        "aggregation_method": "ratio",
        "boundary": "facility",
        "description": (
            "CUE requires carbon emission data, energy data or emission-factor basis, "
            "aggregation period, and calculation method."
        ),
    },
    {
        "metric_namespace": "cim:workflow.energy.per_run",
        "standard_code": "PROV-O",
        "evidence_type": "audit",
        "requirement_level": "recommended",
        "reporting_period": "per_run",
        "aggregation_method": "sum",
        "boundary": "workflow_run",
        "description": (
            "Workflow energy per run requires workflow run ID, execution time window, "
            "node/resource allocation, energy calculation method, and provenance."
        ),
    },
    {
        "metric_namespace": "cim:workflow.energy.per_run",
        "standard_code": "RO-CRATE",
        "evidence_type": "document",
        "requirement_level": "recommended",
        "reporting_period": "per_run",
        "aggregation_method": None,
        "boundary": "workflow_run",
        "description": "RO-Crate packaging of workflow energy evidence for reproducibility.",
    },
]
