# cloud_metrics/scripts/admin_panel.py

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import cloud_metrics.models
from sqlalchemy.orm import configure_mappers
configure_mappers()


from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import streamlit as st
from sqlalchemy import func, or_, and_

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.metric_sample import MetricSample
from cloud_metrics.models.asset import Asset
from cloud_metrics.models.namespace_models import Category, Subcategory
# from cloud_metrics.models.metric_keyword import MetricKeyword

from cloud_metrics.classifiers.ensemble_classifier import classify_metric
from cloud_metrics.registry.namespace_registry import ensure_gd_namespace
from cloud_metrics.services.keyword_learning import learn_keyword
# from cloud_metrics.registry.mapping_registry import register_mapping
from cloud_metrics.utils.unified_key import to_gd
from cloud_metrics.utils.mapping_sync import sync_metric_mapping

st.set_page_config(page_title="CIM – Admin Panel", layout="wide")
st.title("CIM Admin Portal for Unknown Metrics Review")

#  Filters
with st.sidebar:
    st.header("Filters")
    with SessionLocal() as s:
        dcs = s.query(Asset).filter_by(type="datacenter").order_by(Asset.name.asc()).all()
    dc_options = ["(all)"] + [d.name for d in dcs]
    dc_pick = st.selectbox("Datacenter", dc_options, index=0)

    days = st.number_input("Look back (days)", min_value=1, max_value=365, value=7, step=1)
    since = datetime.utcnow() - timedelta(days=int(days))

    search = st.text_input("Search raw_key contains", "")

    limit = st.slider("Max rows", min_value=10, max_value=500, value=100, step=10)

#  helpers
def load_unknowns(s):
    cond_unknown = or_(
        MetricSample.unified_key.like("gd.uncategorized.%"),
        MetricSample.unified_key.like("gd.%.unknown.%"),
    )
    q = (
        s.query(
            MetricSample.raw_key.label("raw_key"),
            func.count(MetricSample.id).label("n"),
            func.max(MetricSample.captured_at).label("last_seen"),
            func.max(MetricSample.source_file).label("source_example"),
        )
        .filter(cond_unknown)
        .filter(MetricSample.captured_at >= since)
    )
    if dc_pick != "(all)":
        # find selected dc id
        dc = s.query(Asset).filter(func.lower(Asset.name) == dc_pick.lower(), Asset.type == "datacenter").first()
        if dc:
            q = q.filter(MetricSample.datacenter_id == dc.id)
        else:
            return []
    if search.strip():
        q = q.filter(MetricSample.raw_key.ilike(f"%{search.strip()}%"))

    q = q.group_by(MetricSample.raw_key).order_by(func.count(MetricSample.id).desc(), func.max(MetricSample.captured_at).desc())
    return q.limit(limit).all()

def load_taxonomy(s):
    cats = s.query(Category).order_by(Category.name.asc()).all()
    subs_by_cat = {}
    for c in cats:
        subs = s.query(Subcategory).filter(Subcategory.category_id == c.id).order_by(Subcategory.name.asc()).all()
        subs_by_cat[c.name] = [sc.name for sc in subs]
    return [c.name for c in cats], subs_by_cat

# ---------- main list ----------
with SessionLocal() as s:
    rows = load_unknowns(s)
    cats, subs_by_cat = load_taxonomy(s)

st.caption(f"Showing {len(rows)} unknown raw keys since {since:%Y-%m-%d %H:%M} UTC"
           + (f" • filtered by datacenter: {dc_pick}" if dc_pick != "(all)" else ""))

if not rows:
    st.success("No unknown metrics in the selected window. Nice!")
    st.stop()

for r in rows:
    raw_key = r.raw_key
    n = int(r.n or 0)
    last_seen = r.last_seen
    src = r.source_example or ""

    with st.expander(f"{raw_key}  •  {n} hits  •  last seen {last_seen:%Y-%m-%d %H:%M:%S}  •  example dc: {src}"):
        # classifier suggestion
        d = classify_metric(raw_key)
        st.write(f"Suggestion: **{d.category}.{d.subcategory}.{d.short_key}** "
                 f"(confidence {d.confidence:.2f}, {d.rationale})")

        # taxonomy pickers
        c1, c2, c3 = st.columns([1,1,1])
        cat = c1.selectbox("Category", cats, index=(cats.index(d.category) if d.category in cats else 0), key=f"cat_{raw_key}")
        subs = subs_by_cat.get(cat, [])
        # pick default subcategory from suggestion when possible
        sub_default_index = subs.index(d.subcategory) if d.subcategory in subs else (0 if subs else 0)
        sub = c2.selectbox("Subcategory", subs or ["(none)"], index=sub_default_index, key=f"sub_{raw_key}")
        short = c3.text_input("Short key", value=d.short_key, key=f"short_{raw_key}")

        # preview unified key
        unified_preview = to_gd(f"gd.{cat}.{sub}.{short}")
        st.code(unified_preview)

        # options
        c4, c5, c6 = st.columns([1,1,2])
        retrofix = c4.checkbox("Update existing rows", value=True, key=f"retro_{raw_key}",
                               help="Update past samples of this raw_key to the approved unified_key.")
        rebuild_json = c5.checkbox("Update mapping JSON", value=True, key=f"json_{raw_key}",
                                   help="Write raw→unified mapping into metric_mapping.json.")
        learn_now = c6.checkbox("Learn keyword (DB)", value=True, key=f"learn_{raw_key}",
                                help="Store raw→(cat,sub,short) in metric_keywords for O(1) next time.")

        if st.button("Approve mapping", key=f"approve_{raw_key}"):
            try:
                # 1) ensure taxonomy rows (auto-create) + normalize unified
                unified_key = ensure_gd_namespace(cat, sub, short, auto_create=True)
                unified_key = to_gd(unified_key)

                # 1.5) Store in the Mapping Registry (cim_mappings table)
                from cloud_metrics.services.mapping_registry_service import create_mapping, approve_mapping
                from cloud_metrics.models.cim_mapping import CimMapping
                from cloud_metrics.models.metric_definition import MetricDefinition
                
                with SessionLocal() as s_map:
                    metric_def = s_map.query(MetricDefinition).filter_by(unified_key=unified_key).first()
                    if not metric_def:
                        # Create metric definition in registry
                        metric_def = MetricDefinition(unified_key=unified_key, status="active")
                        s_map.add(metric_def)
                        s_map.commit()
                        s_map.refresh(metric_def)
                    
                    existing_map = s_map.query(CimMapping).filter_by(source_key=raw_key).first()
                    if existing_map:
                        existing_map.cim_metric_id = metric_def.id
                        existing_map.status = "approved"
                        existing_map.confidence = max(0.95, float(d.confidence or 0))
                        existing_map.rationale = f"Approved via Admin Panel: {d.rationale}"
                        s_map.commit()
                    else:
                        map_record = create_mapping(
                            source_key=raw_key,
                            unified_key=unified_key,
                            relation_type="exactMatch",
                            confidence=max(0.95, float(d.confidence or 0)),
                            rationale=f"Approved via Admin Panel: {d.rationale}"
                        )
                        approve_mapping(map_record.id, approved_by="admin")

                with SessionLocal() as s2:
                    # find a datacenter_id to register mapping (any of the recent samples for this raw_key)
                    dc_entry = (
                        s2.query(MetricSample.datacenter_id)
                        .filter(MetricSample.raw_key == raw_key)
                        .order_by(MetricSample.id.desc())
                        .first()
                    )
                    dc_id = int(dc_entry[0]) if dc_entry else None

                # 2) learn the raw → taxonomy mapping (fast-path next time)
                if learn_now:
                    learn_keyword(raw_key, cat, sub, short, max(0.95, float(d.confidence or 0)))

                # 3) write registry artifacts
                if rebuild_json:
                    try:
                        sync_metric_mapping(unified_key=unified_key, source_key=raw_key)
                    except Exception as jex:
                        st.warning(f"JSON mapping update failed: {jex}")

                # 4) retrofix samples if asked
                if retrofix:
                    with SessionLocal() as s3:
                        s3.query(MetricSample).filter(
                            MetricSample.raw_key == raw_key,
                            or_(
                                MetricSample.unified_key.like("gd.uncategorized.%"),
                                MetricSample.unified_key.like("gd.%.unknown.%"),
                            ),
                        ).update(
                            {MetricSample.unified_key: unified_key},
                            synchronize_session=False
                        )
                        s3.commit()

                st.success(f"Approved: {raw_key} → {unified_key}")
            except Exception as ex:
                st.error(f"Approval failed: {ex}")

# maintenance tools
st.divider()
st.subheader("Maintenance")

colA, colB = st.columns([1,1])

with colA:
    if st.button("Rebuild mapping JSON file"):
        try:
            # assuming script function importable. If it's CLI-only, calling the CLI via subprocess.
            from cloud_metrics.exporters.rebuild_mapping_json import rebuild_mapping
            path = rebuild_mapping()
            st.success(f"Rebuilt: {path}")
        except Exception as ex:
            st.error(f"Rebuild failed: {ex}")

with colB:
    if st.button("Clear classifier cache"):
        try:
            from cloud_metrics.classifiers import ensemble_classifier as EC
            if hasattr(EC.classify_metric, "cache_clear"):
                EC.classify_metric.cache_clear()
            st.success("Classifier cache cleared.")
        except Exception as ex:
            st.error(f"Cache clear failed: {ex}")
