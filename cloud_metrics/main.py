# cloud_metrics/main.py

from fastapi import FastAPI

# Routers
from cloud_metrics.api import metrics, query

app = FastAPI(title="Cloud Metrics API", version="0.1.0")

# Mount endpoints
app.include_router(metrics.router, prefix="/metrics", tags=["ingest"])
app.include_router(query.router,   prefix="/query",   tags=["query"])

@app.get("/health")
async def health():
    return {"status": "ok"}
