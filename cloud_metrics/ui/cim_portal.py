"""CIM admin portal views (Milestone 14).

Read-only registry browse + review/KPI/evidence/provenance via backend services.
Does not mutate ``cim_*`` tables except through ``AdminReviewService`` /
``KpiCalculationService``.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from cloud_metrics.registry.evidence import EvidenceRegistryService
from cloud_metrics.registry.kpi import KpiInput, get_kpi_calculation_service
from cloud_metrics.registry.lifecycle import LifecycleRegistryService
from cloud_metrics.registry.provenance import ProvenanceRegistryService
from cloud_metrics.registry.review import (
    ReviewAction,
    ReviewEntityType,
    get_admin_review_service,
)
from cloud_metrics.registry.standards import StandardsRegistryService

REPORTABLE_NAMESPACES = (
    "cim:energy.efficiency.pue",
    "cim:energy.efficiency.wue",
    "cim:energy.efficiency.cue",
    "cim:workflow.energy.per_run",
)

REGISTRY_CHOICES = (
    "metric",
    "mapping",
    "unit",
    "source",
    "asset",
    "standards",
    "lifecycle",
    "rule",
    "evidence",
    "provenance",
    "extension",
)

_ACTIVITY_ORDER = (
    "orchestration",
    "registry_mapping_lookup",
    "legacy_fallback",
    "unit_validation",
    "source_resolution",
    "asset_resolution",
    "lifecycle_mapping_retrieval",
    "standards_mapping_retrieval",
    "validation_rule_application",
    "evidence_requirement_retrieval",
    "extension_candidate_creation",
    "unresolved_metric_handling",
    "kpi_calculation",
    "review_action",
)


def _row_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if is_dataclass(obj):
        return {k: v for k, v in asdict(obj).items() if k != "extra"}
    skip = {"metadata", "registry", "quantity_kind", "canonical_unit", "metric", "standard"}
    out: Dict[str, Any] = {}
    for col in getattr(obj, "__table__", None).columns if hasattr(obj, "__table__") else []:
        if col.key in skip:
            continue
        val = getattr(obj, col.key, None)
        out[col.key] = val
    return out


def load_registry_rows(session: Session, registry: str) -> List[Dict[str, Any]]:
    """Read-only list of CIM registry rows for the browser."""
    from cloud_metrics.models.cim_registry import (
        CimAsset,
        CimEvidenceRequirement,
        CimExtensionMetric,
        CimLifecycleStage,
        CimMetricDefinition,
        CimMetricMapping,
        CimProvenanceRecord,
        CimSource,
        CimStandard,
        CimUnit,
        CimValidationRule,
    )

    model_map = {
        "metric": CimMetricDefinition,
        "mapping": CimMetricMapping,
        "unit": CimUnit,
        "source": CimSource,
        "asset": CimAsset,
        "standards": CimStandard,
        "lifecycle": CimLifecycleStage,
        "rule": CimValidationRule,
        "evidence": CimEvidenceRequirement,
        "provenance": CimProvenanceRecord,
        "extension": CimExtensionMetric,
    }
    model = model_map.get(registry)
    if model is None:
        raise ValueError(f"Unknown registry '{registry}'")
    rows = session.query(model).all()
    out = [_row_dict(r) for r in rows]
    if registry == "metric":
        for r, orm in zip(out, rows):
            r["quantity_kind"] = orm.quantity_kind.name if orm.quantity_kind else None
            r["canonical_unit"] = orm.canonical_unit.symbol if orm.canonical_unit else None
    if registry == "mapping":
        for r, orm in zip(out, rows):
            r["cim_namespace"] = orm.metric.namespace if orm.metric else None
            r["standard_code"] = orm.standard.code if orm.standard else None
    if registry == "evidence":
        for r, orm in zip(out, rows):
            r["metric_namespace"] = orm.metric.namespace if orm.metric else None
            r["standard_code"] = orm.standard.code if orm.standard else None
    if registry == "unit":
        for r, orm in zip(out, rows):
            r["quantity_kind"] = orm.quantity_kind.name if orm.quantity_kind else None
    return out


def filter_registry_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    status: Optional[str] = None,
    review_status: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter browser rows by status / review_status / text search."""
    needle = (search or "").strip().lower()
    out: List[Dict[str, Any]] = []
    for row in rows:
        if status and status != "(all)":
            if str(row.get("status") or "").lower() != status.lower():
                continue
        if review_status and review_status != "(all)":
            if str(row.get("review_status") or "").lower() != review_status.lower():
                continue
        if needle:
            blob = " ".join(str(v) for v in row.values() if v is not None).lower()
            if needle not in blob:
                continue
        out.append(row)
    return out


def readiness_rows(session: Session) -> List[Dict[str, Any]]:
    """Evidence readiness for seeded reportable metrics / KPIs."""
    ev = EvidenceRegistryService(session=session)
    std = StandardsRegistryService(session=session)
    life = LifecycleRegistryService(session=session)
    rows: List[Dict[str, Any]] = []
    for ns in REPORTABLE_NAMESPACES:
        ev_res = ev.get_requirements_for_metric(ns)
        std_res = std.get_mappings_for_metric(ns, allow_approved=True)
        life_res = life.get_links_for_metric(ns)
        mandatory = list(ev_res.mandatory)
        optional = list(ev_res.optional)
        # Fulfillment is not stored — mandatory items are "declared, not fulfilled"
        missing = [
            {
                "standard_code": m.standard_code,
                "evidence_type": m.evidence_type,
                "description": m.description,
            }
            for m in mandatory
        ]
        rows.append(
            {
                "namespace": ns,
                "readiness_status": ev_res.readiness_status,
                "mandatory_count": len(mandatory),
                "optional_count": len(optional),
                "missing_fulfillment_count": len(missing),
                "mandatory": [
                    {
                        "standard_code": m.standard_code,
                        "evidence_type": m.evidence_type,
                        "requirement_level": m.requirement_level,
                        "boundary": m.boundary,
                        "reporting_period": m.reporting_period,
                        "description": m.description,
                    }
                    for m in mandatory
                ],
                "optional": [
                    {
                        "standard_code": m.standard_code,
                        "evidence_type": m.evidence_type,
                        "requirement_level": m.requirement_level,
                        "description": m.description,
                    }
                    for m in optional
                ],
                "missing_fulfillment": missing,
                "lifecycle_stages": list(life_res.stages),
                "standards_relations": [
                    {"standard_code": m.standard_code, "relation_type": m.relation_type}
                    for m in std_res.mappings
                ],
            }
        )
    return rows


def perform_review_action(
    session: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    *,
    reviewer: str,
    notes: Optional[str] = None,
    edits: Optional[Dict[str, Any]] = None,
    merge_target_namespace: Optional[str] = None,
    allow_exact_match: bool = False,
):
    """Single UI entry point — always goes through AdminReviewService."""
    svc = get_admin_review_service(session)
    return svc.apply(
        entity_type,
        entity_id,
        action,
        reviewer=reviewer,
        notes=notes,
        edits=edits,
        merge_target_namespace=merge_target_namespace,
        allow_exact_match=allow_exact_match,
        commit=True,
    )


def load_provenance_timeline(
    session: Session,
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    prov = ProvenanceRegistryService(session=session)
    if entity_type and entity_id is not None:
        entries = prov.get_chain(entity_type, int(entity_id))
    else:
        entries = prov.list_entries()
    rows = []
    for e in entries[:limit]:
        rows.append(
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "activity": e.activity,
                "agent": e.agent,
                "method": e.method,
                "started_at": e.started_at,
                "inputs": e.inputs,
                "outputs": e.outputs,
                "notes": e.notes,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Streamlit renderers
# ---------------------------------------------------------------------------


def render_registry_browser(st, session: Session) -> None:
    st.subheader("Registry browser")
    st.caption("Read-only view of ``cim_*`` catalogues. Mutations go through Candidate review.")
    registry = st.selectbox("Registry", REGISTRY_CHOICES, key="cim_reg_name")
    c1, c2, c3 = st.columns(3)
    status = c1.text_input("Status filter", value="(all)", key="cim_reg_status")
    review = c2.text_input("Review status filter", value="(all)", key="cim_reg_review")
    search = c3.text_input("Search", value="", key="cim_reg_search")
    try:
        rows = load_registry_rows(session, registry)
    except Exception as exc:
        st.error(str(exc))
        return
    filtered = filter_registry_rows(
        rows, status=status, review_status=review, search=search
    )
    st.caption(f"{len(filtered)} / {len(rows)} entries")
    if not filtered:
        st.info("No rows match the current filters.")
        return
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    ids = [r.get("id") for r in filtered if r.get("id") is not None]
    if ids:
        pick = st.selectbox("Details for id", ids, key="cim_reg_detail")
        detail = next((r for r in filtered if r.get("id") == pick), None)
        if detail:
            st.json(detail)


def render_candidate_review(st, session: Session, reviewer: str) -> None:
    st.subheader("Candidate review queue")
    st.caption("All actions call ``AdminReviewService``. The UI does not write ``cim_*`` rows directly.")
    types = ["(all)"] + [e.value for e in ReviewEntityType]
    type_pick = st.selectbox("Entity type", types, key="cim_rev_type")
    svc = get_admin_review_service(session)
    wanted = None if type_pick == "(all)" else [type_pick]
    entries = svc.list_pending(entity_types=wanted)
    if not entries:
        st.success("No candidate / under_review entries.")
        return
    table = [e.to_dict() for e in entries]
    for row in table:
        row.pop("details", None)
    st.dataframe(table, use_container_width=True, hide_index=True)

    labels = [
        f"{e.entity_type.value}:{e.entity_id} {e.namespace_or_key or e.label or ''}"
        for e in entries
    ]
    choice = st.selectbox("Select entry", list(range(len(entries))), format_func=lambda i: labels[i], key="cim_rev_pick")
    entry = entries[choice]
    st.json(entry.to_dict())

    notes = st.text_area("Review notes", key="cim_rev_notes")
    edits_just = st.text_input("Edit justification (optional, applied with Edit/Approve)", key="cim_rev_just")
    merge_ns = st.text_input("Merge target CIM namespace", key="cim_rev_merge")
    allow_exact = st.checkbox("Allow exactMatch on standards mapping approve", value=False, key="cim_rev_exact")

    actions = [
        ReviewAction.MARK_UNDER_REVIEW,
        ReviewAction.APPROVE,
        ReviewAction.REJECT,
        ReviewAction.EDIT,
        ReviewAction.MERGE,
        ReviewAction.PROMOTE_TO_SEED,
        ReviewAction.DEPRECATE,
        ReviewAction.REQUEST_CHANGES,
        ReviewAction.REOPEN,
    ]
    cols = st.columns(3)
    for i, act in enumerate(actions):
        if cols[i % 3].button(act.value.replace("_", " ").title(), key=f"cim_rev_btn_{act.value}"):
            if not (reviewer or "").strip():
                st.error("Set Reviewer in the sidebar.")
                return
            edits = {}
            if edits_just.strip():
                edits["justification"] = edits_just.strip()
            decision = perform_review_action(
                session,
                entry.entity_type.value,
                entry.entity_id,
                act.value,
                reviewer=reviewer.strip(),
                notes=notes or None,
                edits=edits or None,
                merge_target_namespace=merge_ns.strip() or None,
                allow_exact_match=allow_exact,
            )
            if decision.ok:
                st.success(
                    f"{act.value}: {decision.previous_status} -> {decision.new_status} "
                    f"(provenance {decision.provenance_record_id})"
                )
                if decision.seed_proposal_path:
                    st.info(f"Seed proposal: {decision.seed_proposal_path}")
                st.json(decision.to_dict())
            else:
                st.error(decision.message or "Review action failed")
                st.json(decision.to_dict())


def render_evidence_readiness(st, session: Session) -> None:
    st.subheader("Evidence readiness")
    st.caption(
        "Declared ISO/PROV evidence for reportable KPIs. "
        "Fulfillment artifacts are not stored — mandatory items appear as missing fulfillment."
    )
    rows = readiness_rows(session)
    summary = [
        {
            "namespace": r["namespace"],
            "readiness_status": r["readiness_status"],
            "mandatory": r["mandatory_count"],
            "optional": r["optional_count"],
            "missing_fulfillment": r["missing_fulfillment_count"],
            "lifecycle": ", ".join(r["lifecycle_stages"]),
        }
        for r in rows
    ]
    st.dataframe(summary, use_container_width=True, hide_index=True)
    ns = st.selectbox("Details", [r["namespace"] for r in rows], key="cim_ev_ns")
    detail = next(r for r in rows if r["namespace"] == ns)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Mandatory / required**")
        st.json(detail["mandatory"])
        st.markdown("**Missing fulfillment**")
        st.json(detail["missing_fulfillment"])
    with c2:
        st.markdown("**Optional / recommended**")
        st.json(detail["optional"])
        st.markdown("**Standards mappings**")
        st.json(detail["standards_relations"])
        st.markdown("**Lifecycle stages**")
        st.write(detail["lifecycle_stages"])


def render_kpi_calculator(st, session: Session) -> None:
    st.subheader("KPI calculation (PUE / WUE / CUE)")
    st.caption("Calls ``KpiCalculationService``. Blocked / missing_input is shown as-is — no fake values.")
    kpi = st.selectbox("KPI", ["pue", "wue", "cue"], key="cim_kpi_kind")
    period = st.text_input("Aggregation period", value="monthly", key="cim_kpi_period")
    boundary = st.text_input("Boundary", value="facility", key="cim_kpi_boundary")
    it_v = st.number_input("IT equipment energy", value=800.0, key="cim_kpi_it")
    it_u = st.text_input("IT energy unit", value="kWh", key="cim_kpi_itu")
    allow_cand = st.checkbox("Allow candidate inputs (review override)", value=False, key="cim_kpi_cand")

    extra: Dict[str, Any] = {}
    if kpi == "pue":
        extra["fac_v"] = st.number_input("Total facility energy", value=1200.0, key="cim_kpi_fac")
        extra["fac_u"] = st.text_input("Facility energy unit", value="kWh", key="cim_kpi_facu")
    elif kpi == "wue":
        extra["w_v"] = st.number_input("Water usage", value=2.5, key="cim_kpi_w")
        extra["w_u"] = st.text_input("Water unit", value="m3", key="cim_kpi_wu")
    else:
        extra["c_v"] = st.number_input("Carbon emission", value=250.0, key="cim_kpi_c")
        extra["c_u"] = st.text_input("Carbon unit", value="kgCO2e", key="cim_kpi_cu")

    if st.button("Calculate", key="cim_kpi_run"):
        svc = get_kpi_calculation_service(session)
        it_in = KpiInput(name="it_equipment_energy", value=float(it_v), unit=it_u)
        common = dict(
            aggregation_period=period or None,
            boundary=boundary or None,
            allow_candidate_inputs=allow_cand,
        )
        if kpi == "pue":
            result = svc.calculate_pue(
                KpiInput(name="total_facility_energy", value=float(extra["fac_v"]), unit=extra["fac_u"]),
                it_in,
                **common,
            )
        elif kpi == "wue":
            result = svc.calculate_wue(
                KpiInput(name="water_usage_total", value=float(extra["w_v"]), unit=extra["w_u"]),
                it_in,
                **common,
            )
        else:
            result = svc.calculate_cue(
                KpiInput(name="carbon_emission_operational", value=float(extra["c_v"]), unit=extra["c_u"]),
                it_in,
                **common,
            )
        session.commit()
        status = result.calculation_status
        if status == "calculated" and result.reportable_approved:
            st.success(f"{result.kpi_namespace} = {result.value} {result.unit}")
        else:
            st.warning(f"Status: {status} (approved={result.reportable_approved})")
            if result.value is None:
                st.info("No calculated value (blocked or invalid).")
        if result.errors:
            st.error(result.errors)
        if result.warnings:
            st.warning(result.warnings)
        st.write(f"Provenance record: {result.provenance_record_id}")
        st.json(result.to_dict())


def render_provenance_timeline(st, session: Session) -> None:
    st.subheader("Provenance timeline")
    st.caption(
        "Orchestration, review, and KPI calculation records from ``cim_provenance_records``. "
        "Review actions use entity_type ``cim_<kind>`` (e.g. ``cim_mapping``)."
    )
    entity_type = st.text_input("Entity type (optional)", value="", key="cim_prov_et")
    entity_id_raw = st.text_input("Entity id (optional)", value="", key="cim_prov_id")
    entity_id = int(entity_id_raw) if entity_id_raw.strip().isdigit() else None
    rows = load_provenance_timeline(
        session,
        entity_type=entity_type.strip() or None,
        entity_id=entity_id,
    )
    if not rows:
        st.info("No provenance records for this filter.")
        return
    # Prefer known activity order when present
    def _sort_key(r: Dict[str, Any]):
        act = r.get("activity") or ""
        try:
            return (_ACTIVITY_ORDER.index(act), r.get("id") or 0)
        except ValueError:
            return (len(_ACTIVITY_ORDER), r.get("id") or 0)

    ordered = sorted(rows, key=_sort_key)
    st.dataframe(
        [
            {
                "id": r["id"],
                "activity": r["activity"],
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "agent": r["agent"],
                "started_at": r["started_at"],
                "notes": r["notes"],
            }
            for r in ordered
        ],
        use_container_width=True,
        hide_index=True,
    )
    pick = st.selectbox("Record detail", [r["id"] for r in ordered], key="cim_prov_pick")
    detail = next(r for r in ordered if r["id"] == pick)
    st.json(detail)
