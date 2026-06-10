# cloud_metrics/utils/config.py

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Union

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Settings(BaseSettings):
    # Core Postgres DB
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    # Influx DB
    INFLUX_URL: Optional[str] = Field(default=None, env="INFLUX_URL")
    INFLUX_TOKEN: Optional[str] = Field(default=None, env="INFLUX_TOKEN")
    INFLUX_ORG: Optional[str] = Field(default=None, env="INFLUX_ORG")
    INFLUX_BUCKET: Optional[str] = Field(default=None, env="INFLUX_BUCKET")

    # CORS
    # Accepts JSON list or comma-separated string.
    CORS_ORIGINS: Optional[Union[List[str], str]] = Field(default=None, env="CORS_ORIGINS")

    # Mapping JSON path (canonical)
    METRIC_MAPPING_JSON_PATH: Optional[str] = Field(default=None, env="METRIC_MAPPING_JSON_PATH")

    # --- Debug (optional) ---
    DEBUG_CONFIG: bool = Field(default=False, env="DEBUG_CONFIG")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",  # tolerate unknown env vars (prevents extra_forbidden)
        case_sensitive=False,
    )

    def cors_origins_list(self) -> List[str]:
        v = self.CORS_ORIGINS
        if v is None:
            return ["http://localhost:3000"]
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        # string: try JSON first, then comma-split
        s = str(v).strip()
        if s.startswith("["):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [str(x).strip() for x in arr if str(x).strip()]
            except Exception:
                pass
        return [x.strip() for x in s.split(",") if x.strip()]


# Back-compat alias
DBSettings = Settings

@lru_cache
def get_settings() -> Settings:
    return Settings()


# Back-compat function name
def settings() -> Settings:
    return get_settings()


# --- SQLAlchemy engine/session (single source of truth) ---
_engine = create_engine(get_settings().DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)

def get_mapping_path() -> str:
    """
    Canonical file path for metric_mapping.json.
    Uses METRIC_MAPPING_JSON_PATH if set; otherwise defaults to cloud_metrics/data/metric_mapping.json.
    Ensures parent directory exists.
    """
    cfg = get_settings()
    if cfg.METRIC_MAPPING_JSON_PATH:
        p = Path(cfg.METRIC_MAPPING_JSON_PATH)
    else:
        p = Path("cloud_metrics") / "data" / "metric_mapping.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p.resolve())


class _AppSettingsView:
    @property
    def CORS_ORIGINS(self) -> List[str]:
        return get_settings().cors_origins_list()

app_settings = _AppSettingsView()


class _InfluxSettingsView:
    @property
    def INFLUX_URL(self) -> Optional[str]: return get_settings().INFLUX_URL
    @property
    def INFLUX_TOKEN(self) -> Optional[str]: return get_settings().INFLUX_TOKEN
    @property
    def INFLUX_ORG(self) -> Optional[str]: return get_settings().INFLUX_ORG
    @property
    def INFLUX_BUCKET(self) -> Optional[str]: return get_settings().INFLUX_BUCKET

_influx_view = _InfluxSettingsView()

def get_influx_settings() -> _InfluxSettingsView:
    # backward-compatible function returning a view with the expected attributes
    return _influx_view


# Print once if explicitly enabled
if get_settings().DEBUG_CONFIG:
    cfg = get_settings()
    print(f"[config] DB={cfg.DATABASE_URL}")
    print(f"[config] CORS={cfg.cors_origins_list()}")
    print(f"[config] MAP={get_mapping_path()}")


__all__ = [
    "Settings", "DBSettings", "get_settings", "settings",
    "_engine", "SessionLocal", "get_mapping_path",
    "app_settings", "get_influx_settings",
]
