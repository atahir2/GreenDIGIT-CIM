# cloud_metrics/scripts/streamlit_uploader.py
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import cloud_metrics.models
from sqlalchemy.orm import configure_mappers
configure_mappers()


import json
import os
import tempfile
from datetime import datetime

import streamlit as st

# ---  existing services/utilities ---
from cloud_metrics.services.influx_service import write_mapped_metrics
from cloud_metrics.services.insert_datacenter import get_or_create_datacenter_id
from cloud_metrics.services.insert_file_upload_log import insert_file_upload_log
from cloud_metrics.services.insert_metric_definition import insert_metric_definition
from cloud_metrics.ingestion.automated_mapper import process_metric_sample
from cloud_metrics.exporters.external_json import build_metadata, write_external_metrics_json

# legacy parser (fallback only)
from cloud_metrics.mapping.namespace_mapper_core import parse_and_extract_file_metrics

# NEW robust loader (format + structure agnostic)
from cloud_metrics.utils.ingest_any import load_any_file
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.demo.cim_demonstrator import ensure_workload_mappings
from cloud_metrics.registry.export import get_export_service


def _json_bytes(obj: object) -> str:
    return json.dumps(obj, default=str, indent=2)


def _namespaces_from_orch(orch_rows: list) -> list[str]:
    seen: list[str] = []
    for row in orch_rows:
        ns = row.get("cim_namespace")
        if ns and ns not in seen:
            seen.append(ns)
    return seen


def _table_from_orch(orch_rows: list) -> tuple[list[dict], list[str]]:
    table_rows: list[dict] = []
    unit_flags: list[str] = []
    for row in orch_rows:
        unit_status = row.get("unit_validation_status")
        table_rows.append(
            {
                "raw_key": row.get("raw_metric_name"),
                "observed_value": row.get("observed_value"),
                "cim_namespace": row.get("cim_namespace"),
                "resolved": row.get("resolved"),
                "path": row.get("resolution_path"),
                "mapping_status": row.get("mapping_status"),
                "unit": unit_status,
                "canonical_unit": row.get("canonical_unit"),
                "source": row.get("source_resolution_status"),
                "asset": row.get("asset_resolution_status"),
                "lifecycle": ", ".join(row.get("lifecycle_stages") or []),
                "standards": ", ".join(row.get("standards_relation_types") or []),
                "evidence": row.get("evidence_readiness_status"),
                "provenance_id": row.get("provenance_record_id"),
                "extension_id": row.get("extension_candidate_id"),
                "review_required": row.get("review_required"),
            }
        )
        if unit_status in {"incompatible", "invalid", "conflict"}:
            unit_flags.append(
                f"{row.get('raw_metric_name')}: unit {unit_status} "
                f"(observed={row.get('observed_unit')}, expected={row.get('canonical_unit')})"
            )
    return table_rows, unit_flags


def _samples_from_orch(orch_rows: list) -> list[dict]:
    samples: list[dict] = []
    for row in orch_rows:
        samples.append(
            {
                "raw_key": row.get("raw_metric_name"),
                "observed_value": row.get("observed_value"),
                "observed_unit": row.get("observed_unit"),
                "canonical_unit": row.get("canonical_unit"),
                "cim_namespace": row.get("cim_namespace"),
                "unified_key": row.get("storage_unified_key") or row.get("legacy_unified_key"),
            }
        )
    return samples


def _build_export_packs(orch_rows: list, mapped: dict, header: dict) -> tuple[dict, dict]:
    """Workload-scoped pack + full CIM catalogue pack (existing ExportService)."""
    namespaces = _namespaces_from_orch(orch_rows)
    samples = _samples_from_orch(orch_rows)
    prov_ids = {
        row.get("provenance_record_id")
        for row in orch_rows
        if row.get("provenance_record_id") is not None
    }
    ext_ids = {
        row.get("extension_candidate_id")
        for row in orch_rows
        if row.get("extension_candidate_id") is not None
    }

    def _ns_of(row: dict) -> str | None:
        return row.get("cim_namespace") or row.get("namespace") or row.get("metric_namespace")

    with SessionLocal() as export_session:
        svc = get_export_service(export_session)
        catalogue = {
            "json": svc.export_json(),
            "jsonld": svc.export_jsonld(include_all_metrics=True),
            "provenance": svc.export_provenance(),
            "crosswalk": svc.export_standards_crosswalk(),
            "evidence": svc.export_evidence_readiness(),
        }
        ns_set = set(namespaces)
        full_json = catalogue["json"]
        workload_json = {
            "scope": "workload_ingest",
            "source_file": header.get("source_file"),
            "parser": header.get("parser"),
            "datacenter": header.get("datacenter"),
            "site_id": header.get("site_id"),
            "captured_at": header.get("captured_at"),
            "domain": header.get("domain"),
            "metrics_written": len(mapped),
            "observed_samples": samples,
            "unified_keys": mapped,
            "cim_namespaces": namespaces,
            "orchestration": orch_rows,
            "format": "json",
            "profile": full_json.get("profile"),
            "metric_definitions": [
                m
                for m in (full_json.get("metric_definitions") or [])
                if _ns_of(m) in ns_set
            ],
            "metric_mappings": [
                m
                for m in (full_json.get("metric_mappings") or [])
                if _ns_of(m) in ns_set
            ],
            "standards_mappings": [
                m
                for m in (full_json.get("standards_mappings") or [])
                if _ns_of(m) in ns_set
            ],
            "lifecycle_mappings": [
                m
                for m in (full_json.get("lifecycle_mappings") or [])
                if _ns_of(m) in ns_set
            ],
            "evidence_requirements": [
                m
                for m in (full_json.get("evidence_requirements") or [])
                if _ns_of(m) in ns_set
            ],
            "provenance_records": [
                rec
                for rec in (full_json.get("provenance_records") or [])
                if rec.get("id") in prov_ids
            ],
            "extension_candidates": [
                e
                for e in (full_json.get("extension_candidates") or [])
                if e.get("id") in ext_ids or _ns_of(e) in ns_set
            ],
        }

        graph = []
        ctx = None
        for ns in namespaces:
            doc = svc.export_jsonld(metric_namespace=ns)
            if ctx is None:
                ctx = doc.get("@context")
            graph.append(
                {k: v for k, v in doc.items() if k not in {"@context", "compliance", "profile"}}
            )
        workload_jsonld = {
            "scope": "workload_ingest",
            "source_file": header.get("source_file"),
            "@context": ctx,
            "@graph": graph,
            "note": "Partial JSON-LD for namespaces resolved from this ingest only.",
        }

        all_prov = catalogue["provenance"]
        workload_prov = {
            "scope": "workload_ingest",
            "source_file": header.get("source_file"),
            "format": "provenance",
            "provenance_ids": sorted(prov_ids),
            "extension_ids": sorted(ext_ids),
            "records": [
                rec
                for rec in (all_prov.get("records") or [])
                if rec.get("id") in prov_ids
            ],
        }

        ns_set = set(namespaces)
        all_cross = catalogue["crosswalk"]
        workload_cross = {
            "scope": "workload_ingest",
            "source_file": header.get("source_file"),
            "format": "standards_crosswalk",
            "mappings": [
                m
                for m in (all_cross.get("mappings") or [])
                if m.get("cim_namespace") in ns_set
            ],
        }

        workload_evidence = {
            "scope": "workload_ingest",
            "source_file": header.get("source_file"),
            "metrics": [
                svc.export_evidence_readiness(metric_namespace=ns) for ns in namespaces
            ],
        }

    return {
        "json": _json_bytes(workload_json),
        "jsonld": _json_bytes(workload_jsonld),
        "provenance": _json_bytes(workload_prov),
        "crosswalk": _json_bytes(workload_cross),
        "evidence": _json_bytes(workload_evidence),
    }, {
        "json": _json_bytes(catalogue["json"]),
        "jsonld": _json_bytes(catalogue["jsonld"]),
        "provenance": _json_bytes(catalogue["provenance"]),
        "crosswalk": _json_bytes(catalogue["crosswalk"]),
        "evidence": _json_bytes(catalogue["evidence"]),
    }


def _render_downloads(stem: str, workload: dict, catalogue: dict) -> None:
    st.subheader("Downloads")
    st.caption(
        "This ingest = observed values from the file plus CIM enrichment for those metrics. "
        "CIM catalogues = metric definitions and mappings for the whole registry "
        "(no sample values — those live in Postgres metric_samples / Workload JSON)."
    )
    st.markdown("**This ingest**")
    w1, w2, w3, w4, w5 = st.columns(5)
    w1.download_button(
        "Workload JSON",
        workload["json"],
        file_name=f"{stem}_workload.json",
        mime="application/json",
        key="dl_wl_json",
    )
    w2.download_button(
        "Workload JSON-LD",
        workload["jsonld"],
        file_name=f"{stem}_workload.jsonld",
        mime="application/ld+json",
        key="dl_wl_jsonld",
    )
    w3.download_button(
        "Workload provenance",
        workload["provenance"],
        file_name=f"{stem}_workload_provenance.json",
        mime="application/json",
        key="dl_wl_prov",
    )
    w4.download_button(
        "Workload crosswalk",
        workload["crosswalk"],
        file_name=f"{stem}_workload_crosswalk.json",
        mime="application/json",
        key="dl_wl_cross",
    )
    w5.download_button(
        "Workload evidence",
        workload["evidence"],
        file_name=f"{stem}_workload_evidence.json",
        mime="application/json",
        key="dl_wl_ev",
    )

    st.markdown("**CIM catalogues (full system)**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.download_button(
        "CIM JSON",
        catalogue["json"],
        file_name="cim_catalogue.json",
        mime="application/json",
        key="dl_cat_json",
    )
    c2.download_button(
        "CIM JSON-LD",
        catalogue["jsonld"],
        file_name="cim_catalogue.jsonld",
        mime="application/ld+json",
        key="dl_cat_jsonld",
    )
    c3.download_button(
        "CIM provenance",
        catalogue["provenance"],
        file_name="cim_catalogue_provenance.json",
        mime="application/json",
        key="dl_cat_prov",
    )
    c4.download_button(
        "CIM crosswalk",
        catalogue["crosswalk"],
        file_name="cim_catalogue_crosswalk.json",
        mime="application/json",
        key="dl_cat_cross",
    )
    c5.download_button(
        "CIM evidence",
        catalogue["evidence"],
        file_name="cim_catalogue_evidence.json",
        mime="application/json",
        key="dl_cat_ev",
    )
    st.caption(
        "JSON-LD / RO-Crate / DCAT packages are partial style exports (Milestone 15), "
        "not certified compliance."
    )


def _render_result(result: dict) -> None:
    header = result["header"]
    st.success(
        f"Ingestion complete (registry orchestrator) — **{header.get('source_file')}**"
    )
    st.write(f"Parser: **{header.get('parser')}**")
    st.write(f"Datacenter: **{header.get('datacenter')}**")
    st.write(f"Site ID: **{header.get('site_id')}**")
    st.write(f"Captured at: **{header.get('captured_at')}**")
    st.write(f"Domain: **{header.get('domain')}**")
    st.write(f"Found **{header.get('metric_count')}** metrics")
    st.write("Path: **registry orchestrator** (cim:* + governance)")

    st.subheader("Observed metric values")
    st.caption(
        "Numeric readings from this file. They are stored in Postgres `metric_samples` "
        "(and Influx when available). CIM catalogue downloads list definitions, not these values."
    )
    sample_rows = result.get("samples") or []
    if sample_rows:
        st.dataframe(sample_rows, use_container_width=True)
    else:
        st.json(
            {
                "metrics_written": result.get("metrics_written"),
                "errors": result.get("errors"),
                "unified_keys": result.get("unified_keys"),
            }
        )
    if result.get("influx_warning"):
        st.warning(result["influx_warning"])
    if result.get("output_path"):
        st.write(f"Partner JSON exported: `{result['output_path']}`")

    st.subheader("CIM orchestration results")
    if result.get("table_rows"):
        st.dataframe(result["table_rows"], use_container_width=True)
    for flag in result.get("unit_flags") or []:
        st.error(flag)
    if any(r.get("extension_id") for r in (result.get("orch_rows") or [])):
        st.info("Unresolved metrics created or reused extension candidates (not approved).")
    with st.expander("Full orchestrator metadata"):
        st.json(result.get("orch_rows") or [])

    try:
        _render_downloads(
            result.get("stem") or "workload",
            result["workload_exports"],
            result["catalogue_exports"],
        )
    except Exception as e_exp:
        st.warning(f"CIM export download unavailable: {e_exp}")


st.set_page_config(page_title="CIM Workload Ingestion", layout="wide")
st.title("CIM Workload Ingestion")

st.caption(
    "Upload partner metric files (JSON/YAML/XML/CSV/TXT). "
    "Each metric is processed by the registry orchestrator: CIM namespace, "
    "unit validation, source/asset resolution, lifecycle, standards, evidence, "
    "provenance, and extension candidates."
)

uploaded_file = st.file_uploader(
    "Select metrics file",
    type=["json", "yml", "yaml", "xml", "csv", "txt"],
)

actions = st.columns([1, 1, 4])
run = actions[0].button("Ingest", disabled=uploaded_file is None, type="primary")
clear = actions[1].button("Clear results")
if clear:
    st.session_state.pop("last_ingest", None)

if run and uploaded_file:
    temp_path = None
    try:
        suffix = (
            "." + uploaded_file.name.rsplit(".", 1)[-1].lower()
            if "." in uploaded_file.name
            else ""
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = tmp.name

        try:
            meta, raw_metrics = load_any_file(temp_path)
            used_loader = "ingest_any"
        except Exception as e_any:
            st.warning(f"Generic loader failed ({e_any}). Falling back to legacy parser.")
            raw_metrics, _ = parse_and_extract_file_metrics(str(temp_path), datacenter="")
            stem = uploaded_file.name.rsplit(".", 1)[0]
            meta = type("Meta", (), {})()
            meta.datacenter = stem
            meta.captured_at = None
            meta.site_id = f"{stem}.default_node.default_vm"
            meta.ri_id = meta.node_id = meta.vm_id = meta.host = None
            meta.extra = None
            meta.domain = "unknown"
            used_loader = "legacy_core"

        if used_loader == "ingest_any" and not raw_metrics:
            st.warning("Generic loader found no numeric metrics. Falling back to legacy parser.")
            raw_metrics, _ = parse_and_extract_file_metrics(str(temp_path), datacenter="")
            stem = uploaded_file.name.rsplit(".", 1)[0]
            if not getattr(meta, "datacenter", None):
                meta.datacenter = stem
            if not getattr(meta, "site_id", None):
                meta.site_id = f"{stem}.default_node.default_vm"
            used_loader = "legacy_core_empty_fallback"

        origin_label = (meta.datacenter or "").strip() or uploaded_file.name.rsplit(".", 1)[0]
        temp_stem = os.path.basename(temp_path).rsplit(".", 1)[0] if temp_path else ""
        if origin_label.startswith("tmp") or (temp_stem and origin_label == temp_stem):
            origin_label = uploaded_file.name.rsplit(".", 1)[0]
        if meta.site_id and temp_stem and temp_stem in str(meta.site_id):
            meta.site_id = f"{origin_label}.default_node.default_vm"
        dc_id = get_or_create_datacenter_id(origin_label)

        with SessionLocal() as seed_session:
            ensure_workload_mappings(seed_session)

        if not raw_metrics:
            st.error("No numeric metrics detected in this file.")
        else:
            extra_meta = dict(getattr(meta, "extra", None) or {})
            extra_meta.update(
                {
                    "ingestion_path": "streamlit_uploader",
                    "datacenter_name": origin_label,
                    "source": "file_upload",
                    "source_type": "file",
                    "file_name": uploaded_file.name,
                }
            )

            new_mapped_metrics = {}
            errors = 0
            orch_rows: list = []
            skipped: list = []

            for raw_key, value in raw_metrics.items():
                try:
                    unified_key = process_metric_sample(
                        raw_key=str(raw_key),
                        value=float(value),
                        origin=origin_label,
                        captured_at=meta.captured_at,
                        ri_id=getattr(meta, "ri_id", None),
                        node_id=getattr(meta, "node_id", None),
                        vm_id=getattr(meta, "vm_id", None),
                        host=getattr(meta, "host", None),
                        site_id=meta.site_id,
                        extra_meta=extra_meta,
                        domain=getattr(meta, "domain", None),
                        use_registry_orchestrator=True,
                        orchestrator_results=orch_rows,
                    )
                    new_mapped_metrics[unified_key] = float(value)
                    if orch_rows:
                        orch_rows[-1]["observed_value"] = float(value)
                        orch_rows[-1]["storage_unified_key"] = (
                            orch_rows[-1].get("storage_unified_key") or unified_key
                        )
                except Exception as ex:
                    errors += 1
                    skipped.append(f"{raw_key} skipped: {ex}")

            influx_warning = None
            try:
                write_mapped_metrics(new_mapped_metrics, meta.captured_at or datetime.utcnow())
            except Exception as e_influx:
                influx_warning = (
                    f"Influx time-series write skipped (sink unavailable): {e_influx}. "
                    "Postgres samples, mapping, and partner JSON export still proceed."
                )

            insert_file_upload_log(
                filename=uploaded_file.name,
                datacenter_id=dc_id,
                uploaded_by=None,
            )

            meta_out = build_metadata(
                ri_id=getattr(meta, "ri_id", None),
                node_id=getattr(meta, "node_id", None),
                vm_id=getattr(meta, "vm_id", None),
                datacenter=origin_label,
                host=getattr(meta, "host", None),
                timestamp=meta.captured_at or datetime.utcnow(),
                site_id=meta.site_id,
                extra=getattr(meta, "extra", None),
            )
            output_path = write_external_metrics_json(
                metadata=meta_out,
                metrics_unified_values=new_mapped_metrics,
                file_basename=origin_label,
            )

            for unified_key in new_mapped_metrics.keys():
                try:
                    insert_metric_definition(unified_key=unified_key)
                except Exception:
                    pass

            table_rows, unit_flags = _table_from_orch(orch_rows)
            samples = _samples_from_orch(orch_rows)
            header = {
                "source_file": uploaded_file.name,
                "parser": used_loader,
                "datacenter": origin_label,
                "site_id": meta.site_id,
                "captured_at": (meta.captured_at or datetime.utcnow()).isoformat(),
                "domain": getattr(meta, "domain", None),
                "metric_count": len(raw_metrics),
            }
            workload_exports, catalogue_exports = _build_export_packs(
                orch_rows, new_mapped_metrics, header
            )
            st.session_state.last_ingest = {
                "header": header,
                "stem": uploaded_file.name.rsplit(".", 1)[0],
                "unified_keys": new_mapped_metrics,
                "samples": samples,
                "metrics_written": len(new_mapped_metrics),
                "errors": errors,
                "skipped": skipped,
                "orch_rows": orch_rows,
                "table_rows": table_rows,
                "unit_flags": unit_flags,
                "influx_warning": influx_warning,
                "output_path": output_path,
                "workload_exports": workload_exports,
                "catalogue_exports": catalogue_exports,
            }
    except Exception as e:
        st.error(f"Ingestion failed: {e}")
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

result = st.session_state.get("last_ingest")
if result:
    for msg in result.get("skipped") or []:
        st.warning(msg)
    _render_result(result)
elif uploaded_file:
    st.info("Click Ingest to process this file through the registry orchestrator.")
else:
    st.info("Choose a file to start.")

# # cloud_metrics/scripts/streamlit_uploader.py
#
# import os
# import json
# import tempfile
# from datetime import datetime
# import streamlit as st
#
# # Add the project root to Python path
# import sys
# from pathlib import Path
# project_root = Path(__file__).parent.parent.parent
# sys.path.insert(0, str(project_root))
#
# from cloud_metrics.utils.partner_payload import parse_partner_payload_generic
# from cloud_metrics.utils.metadata import parse_partner_metadata
# #from cloud_metrics.mapping.namespace_mapper_core import parse_and_extract_file_metrics
# from cloud_metrics.ingestion.automated_mapper import process_metric_sample
# from cloud_metrics.services.influx_service import write_mapped_metrics
# from cloud_metrics.services.insert_file_upload_log import insert_file_upload_log
# from cloud_metrics.services.insert_metric_definition import insert_metric_definition
# from cloud_metrics.services.insert_datacenter import insert_datacenter
# from cloud_metrics.exporters.external_json import build_metadata, write_external_metrics_json
# from cloud_metrics.classifiers.ensemble_classifier import classify_metric
#
#
#
# st.set_page_config(page_title="CIM - Metrics Ingestion Panel", layout="wide")
# st.title("Common Information Model (CIM) Metrics Ingestion Portal")
#
# uploaded_file = st.file_uploader(
#     "Upload partner JSON (must include metadata + metrics)",
#     type=["json"], accept_multiple_files=False
# )
#
# if not uploaded_file:
#     st.info("Provide a JSON with `metadata` and `metrics`.")
#     st.stop()
#
# temp_path = None
# try:
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
#         tmp.write(uploaded_file.getbuffer())
#         temp_path = tmp.name
#
#     # load and parse
#     doc = json.loads(uploaded_file.getvalue().decode("utf-8-sig"))
#     filename_stem = uploaded_file.name.rsplit(".", 1)[0]
#
#     meta, raw_metrics = parse_partner_payload_generic(doc)
#     # st.success(f"Datacenter: {ingest_meta.datacenter}")
#     # st.caption(f"ri_id={ingest_meta.ri_id} node_id={ingest_meta.node_id} vm_id={ingest_meta.vm_id} "
#     #            f"host={ingest_meta.host} site_id={ingest_meta.site_id} "
#     #            f"timestamp={(ingest_meta.timestamp or datetime.utcnow()).isoformat()}")
#
#     # if not raw_metrics:
#     #     st.warning("No numeric metrics found in file.")
#     #     st.stop()
#
#     new_mapped = {}
#     for raw_key, value in raw_metrics.items():
#         st.write(f"Classifying: {raw_key}")
#         unified_key = process_metric_sample(
#             raw_key=raw_key,
#             value=float(value),
#             origin=meta.datacenter,               # source_file and sources[] = datacenter
#             captured_at=meta.captured_at,
#             site_id=meta.site_id,
#             extra_meta=meta.extra,
#             domain=meta.domain,
#             ri_id=meta.ri_id,
#             node_id=meta.node_id,
#             vm_id=meta.vm_id,
#             host=meta.host,
#         )
#
#         new_mapped[unified_key] = float(value)
#         st.write(f"→ {unified_key}")
#
#     # Influx write
#     write_mapped_metrics(new_mapped, meta.captured_at or datetime.utcnow())
#
#     # Log upload (use an actual dc lookup if you added it)
#     insert_file_upload_log(
#         filename=uploaded_file.name,
#         datacenter_id=1,
#         uploaded_by=None,
#     )
#
#     st.success("Ingestion complete.")
#     st.json({"metrics_written": len(new_mapped)})
#
# except Exception as e:
#     st.error(f"Ingestion failed: {e}")
# finally:
#     if temp_path:
#         import os
#         try:
#             os.remove(temp_path)
#         except Exception: pass
#

# # Form prevents auto-execution while typing; nothing runs until you click "Ingest"
# with st.form("ingest_form", clear_on_submit=False):
#     st.subheader("Metadata (fill this first)")
#     c1, c2, c3 = st.columns(3)
#     ri_id   = c1.text_input("ri_id", value=st.session_state.get("ri_id", ""))
#     node_id = c2.text_input("node_id", value=st.session_state.get("node_id", ""))
#     vm_id   = c3.text_input("vm_id", value=st.session_state.get("vm_id", ""))
#
#     c4, c5 = st.columns(2)
#     datacenter = c4.text_input("datacenter (defaults to filename base)", value=st.session_state.get("datacenter", ""))
#     host       = c5.text_input("host", value=st.session_state.get("host", ""))
#
#     # ISO 8601 like 2025-08-29T12:34:56 or leave blank
#     timestamp_str = st.text_input("timestamp (ISO 8601, optional)", value=st.session_state.get("timestamp", ""))
#
#     st.subheader("Upload")
#     uploaded_file = st.file_uploader(
#         "Select metrics file (.json/.xml/.csv/.yaml/.yml/.txt)",
#         type=["json", "xml", "csv", "yaml", "yml", "txt"],
#     )
#
#     run = st.form_submit_button("Ingest")
#
# if not run:
#     st.info("Fill metadata, choose a file, then click Ingest.")
#     st.stop()
#
# # Persist what you typed for next run
# st.session_state.update({
#     "ri_id": ri_id, "node_id": node_id, "vm_id": vm_id,
#     "datacenter": datacenter, "host": host, "timestamp": timestamp_str
# })
#
# if not uploaded_file:
#     st.warning("Please choose a file to ingest.")
#     st.stop()
#
# temp_path = None
# try:
#     # Determine extension
#     suffix = "." + uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
#
#     # Save uploaded file to a temp path (Windows-safe)
#     with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
#         tmp.write(uploaded_file.getbuffer())
#         temp_path = tmp.name
#
#         # Origin (datacenter label) is what the user typed, else fallback to filename base
#         origin_label = (datacenter or "").strip() or uploaded_file.name.rsplit(".", 1)[0]
#         origin_label = origin_label.strip()
#
#         # Make sure the datacenter exists (idempotent)
#         from cloud_metrics.services.insert_datacenter import get_or_create_datacenter_id
#         dc_id = get_or_create_datacenter_id(origin_label)
#
#         # Parsing JSON if present; otherwise use the generic parser
#         raw_metrics = None
#         captured_at = None
#         is_partner_json = False
#         partner_meta = {}
#
#     # Detect partner JSON shape: {"metadata": {...}, "metrics": {...}}
#     if suffix == ".json":
#         try:
#             with open(temp_path, "r", encoding="utf-8-sig") as f:
#                 doc = json.load(f)
#             if isinstance(doc, dict) and "metadata" in doc and "metrics" in doc:
#                 is_partner_json = True
#                 partner_meta = doc.get("metadata") or {}
#                 raw_metrics = {}
#                 for k, v in (doc.get("metrics") or {}).items():
#                     try:
#                         raw_metrics[str(k)] = float(v)
#                     except (TypeError, ValueError):
#                         st.warning(f"Skipping non-numeric metric '{k}': {v}")
#
#                 # Only override if provided in the file; otherwise keep what user typed
#                 ri_id = partner_meta.get("ri_id") or ri_id
#                 node_id = partner_meta.get("node_id") or node_id
#                 vm_id = partner_meta.get("vm_id") or vm_id
#                 host = partner_meta.get("host") or host
#                 if partner_meta.get("datacenter"):
#                     origin_label = str(partner_meta["datacenter"]).strip()
#                     dc_id = get_or_create_datacenter_id(origin_label)
#
#                 ts_in = partner_meta.get("timestamp")
#                 if ts_in:
#                     try:
#                         captured_at = datetime.fromisoformat(str(ts_in).replace("Z", "+00:00"))
#                     except Exception:
#                         captured_at = None
#         except Exception:
#             raw_metrics = None  # fall back to generic parser below
#
#     if raw_metrics is None:
#         # Parse raw + pre-mapped metrics from file
#         st.write("Parsed file, now mapping metrics…")
#         raw_metrics, _ = parse_and_extract_file_metrics(str(temp_path), datacenter=origin_label)
#
#     st.write(f"Found {len(raw_metrics)} metrics")
#
#     # DEBUG: showing the metadata
#     st.write(
#         f"Using metadata → dc='{origin_label}', ri_id='{ri_id}', node_id='{node_id}', vm_id='{vm_id}', host='{host}', site_id='{'.'.join([_ for _ in [ri_id, node_id, vm_id] if _])}'")
#
#     # Ingest each metric (DB + Influx + JSON mapping)
#     st.write(f"Raw metrics: {list(raw_metrics.keys())}")
#     new_mapped_metrics = {}
#     for raw_key, value in raw_metrics.items():
#         st.write(f"Classifying + mapping: {raw_key}")
#         unified_key = process_metric_sample(
#             raw_key=raw_key,
#             value=float(value),
#             origin=origin_label,
#             captured_at=captured_at,
#             ri_id=ri_id,
#             node_id=node_id,
#             vm_id=vm_id,
#             host=host,
#             site_id=".".join(filter(None, [ri_id, node_id, vm_id])) or None,
#         )
#         new_mapped_metrics[unified_key] = float(value)
#         st.write(f"{raw_key} -> {unified_key}" )
#
#     # Write to InfluxDB (keep legacy function name via alias)
#     st.write("Writing to InfluxDB…")
#     write_mapped_metrics(new_mapped_metrics, captured_at or datetime.utcnow())
#
#     # Logging the upload with datacenter ID
#     insert_file_upload_log(
#             filename=uploaded_file.name,
#             datacenter_id=dc_id,
#             uploaded_by=None,
#     )
#
#     # Build partner JSON with gd.* keys
#     meta = build_metadata(
#             ri_id=ri_id,
#             node_id=node_id,
#             vm_id=vm_id,
#             datacenter=origin_label,
#             host=host,
#             timestamp=captured_at or datetime.utcnow(),
#     )
#     output_path = write_external_metrics_json(
#             metadata=meta,
#             metrics_unified_values=new_mapped_metrics,
#             file_basename=origin_label,
#     )
#
#     st.write("Storing unified metric definitions in PostgreSQL…")
#     for unified_key in new_mapped_metrics.keys():
#         insert_metric_definition(unified_key=unified_key)
#
#     st.success("File ingested and stored successfully.")
#     st.write(f"Partner JSON exported: '{output_path}'")
#
# except Exception as e:
#     st.error(f"❌ Ingestion failed: {e}")
#
# finally:
# # Cleaning up, but don’t crash if it’s already gone or locked
#    if temp_path:
#        try: os.remove(temp_path)
#        except Exception: pass


