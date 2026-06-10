# cloud_metrics/scripts/seed_namespace.py

from sqlalchemy import func
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.namespace_models import Standard, Category, Subcategory

SEED = {
    "iso": {
        "performance": ["cpu", "memory"],
        "storage": ["disk"],
        "network": ["traffic"],
        "energy": ["power", "renewable"],
        "environment": ["temperature"],
    },
    "jrc": {
        "environment": ["temperature"],
    },
}

def _get_or_create_std(s, name: str):
    row = s.query(Standard).filter(func.lower(Standard.name) == name.lower()).first()
    if row:
        return row
    row = Standard(name=name)
    s.add(row)
    s.flush()
    return row

def _get_or_create_cat(s, std_id: int, name: str):
    row = (
        s.query(Category)
        .filter(func.lower(Category.name) == name.lower(), Category.standard_id == std_id)
        .first()
    )
    if row:
        return row
    row = Category(name=name, standard_id=std_id)
    s.add(row)
    s.flush()
    return row

def _get_or_create_sub(s, cat_id: int, name: str):
    row = (
        s.query(Subcategory)
        .filter(func.lower(Subcategory.name) == name.lower(), Subcategory.category_id == cat_id)
        .first()
    )
    if row:
        return row
    row = Subcategory(name=name, category_id=cat_id)
    s.add(row)
    return row

def main():
    with SessionLocal() as s:
        for std_name, cats in SEED.items():
            std = _get_or_create_std(s, std_name)
            for cat_name, subs in cats.items():
                cat = _get_or_create_cat(s, std.id, cat_name)
                for sub_name in subs:
                    _get_or_create_sub(s, cat.id, sub_name)
        s.commit()
        print("✅ Namespace seeded (case-insensitive, idempotent).")

if __name__ == "__main__":
    main()
