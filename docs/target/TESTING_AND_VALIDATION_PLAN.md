# Registry-Driven CIM Architecture: Testing & Validation Plan

This document outlines the testing, regression testing, and data validation protocols implemented to ensure the reliability and functional parity of the registry-driven Common Information Model.

---

## 1. Test Automation Architecture

The test suite runs on `pytest` and leverages an in-memory SQL database configuration to ensure isolation, speed, and repeatability.

### 1.1 In-Memory Database Isolation
For testing service layers and endpoints, we initialize a transient SQLite database:
* **Engine Connection**: `sqlite:///:memory:`
* **Schema Creation**: `Base.metadata.create_all(engine)`
* **Thread-Safety Settings**:
  To prevent connection lock errors or `no such table` failures when Starlette's `TestClient` makes requests across background threadpools, we define:
  ```python
  from sqlalchemy.pool import StaticPool
  
  engine = create_engine(
      "sqlite:///:memory:",
      connect_args={"check_same_thread": False},
      poolclass=StaticPool,
      future=True
  )
  ```
* **Monkeypatch Injection**:
  We dynamically patch `SessionLocal` across all modules within tests to point to a single shared mock Session.

---

## 2. Unit Testing Strategy

Unit tests are implemented under [test_new_services.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_new_services.py) and focus on specific service domain boundaries:

### 2.1 Unit Normalization and Conversion
* **Method**: Tests `unit_registry_service.convert_value()`, `get_canonical_unit()`, and `validate_unit_for_quantity()`.
* **Assertions**:
  * Verify conversion of non-canonical units to canonical ones (e.g. `1500 Wh` converts to `1.5 kWh`).
  * Verify validation failure when mismatched quantity kinds are checked (e.g. `W` is rejected as an `Energy` unit).

### 2.2 Mapping Lifecycle and State Machine
* **Method**: Tests `mapping_registry_service.create_mapping()`, `resolve_mapping()`, and `approve_mapping()`.
* **Assertions**:
  * Verify that a newly proposed mapping is created in `proposed` state.
  * Verify that `resolve_mapping()` returns `None` for unapproved mappings.
  * Verify that calling `approve_mapping()` updates the status to `approved`.
  * Verify that `resolve_mapping()` successfully matches the source key after approval.

### 2.3 Rule Validation Engine
* **Method**: Tests `rule_registry_service.validate_metric_sample()`.
* **Assertions**:
  * Verify `Namespace error` triggers if a sample does not start with `gd.`.
  * Verify `Validation warning` is recorded for missing units on numeric samples.
  * Verify power vs energy unit validation (e.g., rejecting power units for energy metrics).
  * Verify range limit violations (PUE < 1.0, temperatures outside -50 to 150°C, and percentages outside 0-100%).

### 2.4 Provenance Lineage Records
* **Method**: Tests `provenance_registry_service.record_activity()`.
* **Assertions**:
  * Verify that metadata inputs, outputs, methods, and confidence values are written accurately into `provenance_records` database rows.

---

## 3. Integration Testing Strategy

Integration tests are implemented under [test_registry_api.py](file:///z:/GreenDIGIT_CIM_testing_v1/tests/test_registry_api.py) and verify API-to-database routing:

### 3.1 REST API Endpoints Verification
Endpoints are tested using FastAPI's `TestClient` to ensure correct JSON serialization and CRUD functionality:
* **GET `/api/v1/registry/quantity-kinds`**: Asserts listing of seeded dimensions.
* **GET `/api/v1/registry/units`**: Asserts listing of seeded units.
* **GET `/api/v1/registry/metrics`**: Asserts listing of metrics.
* **GET `/api/v1/registry/sources`**: Asserts listing of telemetry sources.
* **GET `/api/v1/registry/assets`**: Asserts listing of assets.
* **POST `/api/v1/registry/mappings`**: Submits a mapping proposal and asserts returned `proposed` state.
* **POST `/api/v1/registry/mappings/{id}/approve`**: Approves a proposal and asserts state promotion to `approved`.
* **GET `/api/v1/registry/provenance`**: Asserts retrieval of lineage logs.

---

## 4. Ingestion Pipeline & Validation Verification

End-to-end telemetry flows are tested via `test_pipeline_ingestion`:
1. A metric definition is registered with canonical unit `kWh` and quantity kind `Energy`.
2. A sample payload containing `2500 Wh` is passed to the automated mapper.
3. **Parity Check**: Asserts that the sample is successfully intercepted, normalizes `2500 Wh` to `2.5 kWh`, runs the validator rules, logs a `unit_conversion` provenance audit trace, and writes a `2.5` value into `MetricSample` under unit `kWh`.
