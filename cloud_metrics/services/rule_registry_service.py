# cloud_metrics/services/rule_registry_service.py

from typing import List, Dict, Any, Optional
from cloud_metrics.services.unit_registry_service import validate_unit_for_quantity

def validate_metric_sample(
    *,
    unified_key: str,
    value: float,
    unit: Optional[str] = None,
    tags: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Validates a metric sample against the registered rules.
    Returns a list of validation errors/warnings.
    """
    violations = []

    # Rule 1: Every metric must have a namespace starting with gd.
    if not unified_key.startswith("gd."):
        violations.append(f"Namespace error: unified key '{unified_key}' must start with 'gd.'")

    # Rule 2: Numeric metrics must have a unit (Warning)
    if unit is None:
        violations.append(f"Validation warning: metric '{unified_key}' is numeric but has no unit specified")

    # Rule 3: Energy vs Power unit consistency
    if "energy" in unified_key.lower():
        # Energy metrics should have Wh, kWh, etc.
        if unit and not validate_unit_for_quantity(unit, "Energy") and not validate_unit_for_quantity(unit, "Percentage"):
            violations.append(f"Unit conflict: energy metric '{unified_key}' has invalid unit '{unit}' (expected Energy quantity unit like kWh)")
            
    if "power" in unified_key.lower():
        # Power metrics should have W, kW, etc.
        if unit and not validate_unit_for_quantity(unit, "Power"):
            violations.append(f"Unit conflict: power metric '{unified_key}' has invalid unit '{unit}' (expected Power quantity unit like W)")

    # Rule 4: PUE must be >= 1.0
    if "pue" in unified_key.lower():
        if value < 1.0:
            violations.append(f"Value range violation: PUE value {value} is less than 1.0")

    # Rule 5: Temperature range check (-50 to 150 °C)
    if "temperature" in unified_key.lower() and unit == "°C":
        if value < -50.0 or value > 150.0:
            violations.append(f"Value range warning: temperature value {value}°C is outside reasonable range (-50 to 150)")

    # Rule 6: Percentage must be 0-100
    # e.g., utilization, CPU usage
    if "utilization" in unified_key.lower() or "percentage" in unified_key.lower():
        if value < 0.0 or value > 100.0:
            violations.append(f"Value range warning: percentage/utilization value {value} is outside 0-100 range")

    return violations
