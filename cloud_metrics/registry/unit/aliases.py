"""Safe unit symbol aliases for CIM Unit Registry lookups.

Maps common lowercase / informal spellings onto seeded ``cim_units.symbol``
values. Does not invent units outside the Milestone 3 catalogue.
"""

from __future__ import annotations

from typing import Dict, Optional

# alias (lowercased, stripped) → canonical registry symbol
UNIT_ALIASES: Dict[str, str] = {
    # Power
    "w": "W",
    "watt": "W",
    "watts": "W",
    "kw": "kW",
    "kilowatt": "kW",
    "kilowatts": "kW",
    # Energy
    "wh": "Wh",
    "watt-hour": "Wh",
    "watthour": "Wh",
    "kwh": "kWh",
    "kw-h": "kWh",
    "kilowatt-hour": "kWh",
    "kilowatthour": "kWh",
    "j": "J",
    "joule": "J",
    "joules": "J",
    # Carbon
    "kgco2e": "kgCO2e",
    "kg_co2e": "kgCO2e",
    "kgco2eq": "kgCO2e",
    "kgco2": "kgCO2e",
    "gco2e": "gCO2e",
    "g_co2e": "gCO2e",
    "gco2eq": "gCO2e",
    "gco2e/kwh": "gCO2e/kWh",
    "g_co2e/kwh": "gCO2e/kWh",
    "gco2eq/kwh": "gCO2e/kWh",
    # Time
    "sec": "s",
    "secs": "s",
    "second": "s",
    "seconds": "s",
    "msec": "ms",
    "millis": "ms",
    "millisecond": "ms",
    "milliseconds": "ms",
    "hr": "h",
    "hour": "h",
    "hours": "h",
    # Data size
    "byte": "B",
    "bytes": "B",
    "kb": "KB",
    "kilobyte": "KB",
    "kilobytes": "KB",
    "kib": "KB",
    "mb": "MB",
    "megabyte": "MB",
    "megabytes": "MB",
    "mib": "MB",
    "gb": "GB",
    "gigabyte": "GB",
    "gigabytes": "GB",
    "gib": "GB",
    "tb": "TB",
    "terabyte": "TB",
    "terabytes": "TB",
    "tib": "TB",
    # Ratio / dimensionless
    "percent": "%",
    "percentage": "%",
    "pct": "%",
    "pc": "%",
    "dimensionless": "dimensionless",
    "unitless": "dimensionless",
    "none": "dimensionless",
    "n/a": "dimensionless",
    "na": "dimensionless",
    # Water
    "l": "L",
    "litre": "L",
    "litres": "L",
    "liter": "L",
    "liters": "L",
    "m^3": "m3",
    "m³": "m3",
    "cubic_m": "m3",
    "cubic_meter": "m3",
    "cubic_metre": "m3",
    "cubic_meters": "m3",
    "cubic_metres": "m3",
    # Count
    "counts": "count",
    "n": "count",
}


def normalize_unit_token(raw: Optional[str]) -> Optional[str]:
    """Strip and collapse whitespace; return None for empty input."""
    if raw is None:
        return None
    token = str(raw).strip()
    if not token:
        return None
    return " ".join(token.split())


def resolve_unit_alias(raw: Optional[str]) -> Optional[str]:
    """Return registry symbol if ``raw`` is a known alias; else normalized token."""
    token = normalize_unit_token(raw)
    if token is None:
        return None
    lower = token.lower()
    if lower in UNIT_ALIASES:
        return UNIT_ALIASES[lower]
    # Also try without spaces/underscores
    compact = lower.replace(" ", "").replace("_", "")
    if compact in UNIT_ALIASES:
        return UNIT_ALIASES[compact]
    return token
