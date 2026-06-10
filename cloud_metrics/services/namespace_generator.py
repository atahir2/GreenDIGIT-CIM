# cloud_metrics/services/namespace_generator.py

from sqlalchemy import func
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.namespace_models import Standard, Category, Subcategory

# optional aliases to match DB naming
CATEGORY_ALIASES = {
    "energy": ["energy", "power_energy"],
    "storage": ["storage", "storage-systems"],
    "network": ["network", "networks"],
    "performance": ["performance"],
    "environment": ["environment", "env"],
}
SUBCATEGORY_ALIASES = {
    "renewable": ["renewable", "renewables", "green"],
    "consumption": ["consumption", "energyuse", "usage", "consumed"],
    "power": ["power"],
    "disk": ["disk", "volume", "filesystem", "fs"],
    "traffic": ["traffic", "throughput", "bandwidth"],
    "cpu": ["cpu"],
    "memory": ["memory", "mem"],
    "temperature": ["temperature", "temp"],
}

def _find_category(session, name: str):
    # try exact (ci)
    row = (session.query(Category)
           .filter(func.lower(Category.name) == name.lower())
           .first())
    if row:
        return row
    # try aliases
    for canon, aliases in CATEGORY_ALIASES.items():
        if name.lower() in (a.lower() for a in aliases):
            row = (session.query(Category)
                   .filter(func.lower(Category.name) == canon.lower())
                   .first())
            if row:
                return row
    return None

def _find_subcategory(session, category_id: int, name: str):
    row = (session.query(Subcategory)
           .filter(func.lower(Subcategory.name) == name.lower(),
                   Subcategory.category_id == category_id)
           .first())
    if row:
        return row
    for canon, aliases in SUBCATEGORY_ALIASES.items():
        if name.lower() in (a.lower() for a in aliases):
            row = (session.query(Subcategory)
                   .filter(func.lower(Subcategory.name) == canon.lower(),
                           Subcategory.category_id == category_id)
                   .first())
            if row:
                return row
    return None

def generate_namespace(category_name: str, subcategory_name: str, metric_short_key: str) -> str:
    """
    Build a fully-qualified unified metric namespace:
      Returns: gd.<category>.<subcategory>.<short>
                ##<standard>.<category>.<subcategory>.<metric_short_key>

    Looks up Standard/Category/Subcategory in SQL via SessionLocal.
    """
    session = SessionLocal()
    try:
        cat = (
            session.query(Category)
            .filter(func.lower(Category.name) == category_name.lower())
            .first()
        )
        if not cat:
            raise ValueError(f"Category not found (case-insensitive): '{category_name}'")

        std = session.query(Standard).filter(Standard.id == cat.standard_id).first()
        if not std:
            raise ValueError(f"No Standard found for category '{cat.name}' (id={cat.id})")

        sub = (
            session.query(Subcategory)
            .filter(
                func.lower(Subcategory.name) == subcategory_name.lower(),
                Subcategory.category_id == cat.id,
            )
            .first()
        )
        if not sub:
            raise ValueError(
                f"Subcategory not found for category '{cat.name}': '{subcategory_name}'"
            )

        return f"{std.name.lower()}.{cat.name}.{sub.name}.{metric_short_key}"
    finally:
        session.close()