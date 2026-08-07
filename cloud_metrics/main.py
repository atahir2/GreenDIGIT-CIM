# cloud_metrics/main.py

from fastapi import FastAPI

# Routers
from cloud_metrics.api import metrics, query, registry_api, cim_review_api

app = FastAPI(title="Cloud Metrics API", version="0.1.0")

# Mount endpoints
app.include_router(metrics.router, prefix="/metrics", tags=["ingest"])
app.include_router(query.router,   prefix="/query",   tags=["query"])
app.include_router(registry_api.router, prefix="/api/v1/registry", tags=["registry"])
app.include_router(
    cim_review_api.router, prefix="/api/v1/cim-review", tags=["cim-review"]
)

@app.get("/health")
async def health():
    return {"status": "ok"}
