"""Milestone 3 registry seed package.

Usage::

    from cloud_metrics.registry.seed import seed_all
    from cloud_metrics.utils.config import SessionLocal

    with SessionLocal() as session:
        report = seed_all(session)
"""

from cloud_metrics.registry.seed.data import RELATION_TYPES
from cloud_metrics.registry.seed.loader import SeedReport, seed_all

__all__ = ["RELATION_TYPES", "SeedReport", "seed_all"]
