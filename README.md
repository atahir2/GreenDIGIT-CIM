# Cloud Metrics

Unified ingestion and query service for cloud metrics.

## Installation

Copy `.env.sample` to `.env` and fill in your environment variables.

Install dependencies:

```bash
poetry install
```

## Running the server

```bash
uvicorn cloud_metrics.main:app --reload
```

## Testing

```bash
pytest
```

## CI

CI pipeline is defined in `.github/workflows/ci.yml`.
