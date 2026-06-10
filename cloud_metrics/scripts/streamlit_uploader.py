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


st.set_page_config(page_title="Cloud Metrics Uploader", layout="centered")
st.title("Ingestion Uploader (Any Format)")

st.caption(
    "Upload partner metric files (JSON/YAML/XML/CSV/TXT). "
    "We’ll auto-extract metadata + numeric metrics, classify, persist, and export gd.* JSON."
)

uploaded_file = st.file_uploader(
    "Select metrics file",
    type=["json", "yml", "yaml", "xml", "csv", "txt"],
)

if not uploaded_file:
    st.info("Choose a file to start.")
    st.stop()

run = st.button("Ingest")
if not run:
    st.stop()

temp_path = None
try:
    # Save uploaded file to a safe temp path
    suffix = (
        "." + uploaded_file.name.rsplit(".", 1)[-1].lower()
        if "." in uploaded_file.name
        else ""
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        temp_path = tmp.name

    # --- Parse meta + metrics (robust path) ---
    try:
        meta, raw_metrics = load_any_file(temp_path)
        used_loader = "ingest_any"
    except Exception as e_any:
        # --- Fallback to legacy core parser ---
        st.warning(f"Generic loader failed ({e_any}). Falling back to legacy parser.")
        st.write("Parsed file (legacy), now mapping metrics…")
        raw_metrics, _ = parse_and_extract_file_metrics(str(temp_path), datacenter="")
        # Synthesize minimal meta from filename when using fallback:
        stem = uploaded_file.name.rsplit(".", 1)[0]
        meta = type("Meta", (), {})()  # lightweight anonymous object
        meta.datacenter = stem
        meta.captured_at = None
        meta.site_id = f"{stem}.default_node.default_vm"
        meta.ri_id = meta.node_id = meta.vm_id = meta.host = None
        meta.extra = None
        meta.domain = "unknown"
        used_loader = "legacy_core"

    # ensure datacenter row
    origin_label = (meta.datacenter or "").strip() or uploaded_file.name.rsplit(".", 1)[0]
    dc_id = get_or_create_datacenter_id(origin_label)

    st.write(f"Parser: **{used_loader}**")
    st.write(f"Datacenter: **{origin_label}**")
    st.write(f"Site ID: **{meta.site_id}**")
    st.write(f"Captured at: **{(meta.captured_at or datetime.utcnow()).isoformat()}**")
    st.write(f"Domain: **{meta.domain}**")
    st.write(f"Found **{len(raw_metrics)}** metrics")

    if not raw_metrics:
        st.error("No numeric metrics detected in this file.")
        st.stop()

    # Ingest metrics (DB + registry + JSON sync) and prepare for Influx
    new_mapped_metrics = {}
    errors = 0

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
                extra_meta=getattr(meta, "extra", None),
                domain=getattr(meta, "domain", None),
            )
            new_mapped_metrics[unified_key] = float(value)
        except Exception as ex:
            errors += 1
            st.warning(f"⚠️ {raw_key} skipped: {ex}")

    # Write valid points to Influx
    write_mapped_metrics(new_mapped_metrics, meta.captured_at or datetime.utcnow())

    # Upload log
    insert_file_upload_log(
        filename=uploaded_file.name,
        datacenter_id=dc_id,
        uploaded_by=None,
    )

    # Export partner JSON (gd.* keys)
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

    # Ensure metric definitions exist (for admin / standards hook)
    for unified_key in new_mapped_metrics.keys():
        try:
            insert_metric_definition(unified_key=unified_key)
        except Exception as e_def:
            st.warning(f"Definition upsert failed for {unified_key}: {e_def}")

    st.success("✅ Ingestion complete.")
    st.json({"metrics_written": len(new_mapped_metrics), "errors": errors})
    st.write(f"Partner JSON exported: `{output_path}`")

except Exception as e:
    st.error(f"❌ Ingestion failed: {e}")

finally:
    # best-effort cleanup
    try:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception:
        pass



















































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


