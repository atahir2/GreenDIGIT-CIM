# cloud_metrics/classifiers/namespace_registry.py

from typing import Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.namespace_models import Category, Subcategory
from cloud_metrics.models.standard_models import Standard

# Optional: mark auto-created rows for review later
AUTO_DESC = "auto-created by registry"

def _get_or_create_gd_standard(session) -> Optional[Standard]:
    #Ensuring a 'gd' Standard exists if your Category model requires standard_id.

    std = session.query(Standard).filter(func.lower(Standard.name) == "gd").first()
    if std:
        return std
    try:
        std = Standard(name="gd", description=AUTO_DESC)  # adjust fields to your model
        session.add(std)
        session.commit()
        return std
    except IntegrityError:
        session.rollback()
        return session.query(Standard).filter(func.lower(Standard.name) == "gd").first()

def _ensure_category(session, name: str) -> Category:
    cat = (session.query(Category)
           .filter(func.lower(Category.name) == name.lower())
           .first())
    if cat:
        return cat

    std = None

    # If Category.standard_id is NOT NULL, ensure 'gd' exists
    try:
        std = _get_or_create_gd_standard(session)
    except Exception:
        std = None
    try:
        cat = Category(name=name.lower(), description=AUTO_DESC)
        if hasattr(Category, "standard_id") and std is not None:
            cat.standard_id = std.id  # type: ignore[attr-defined]
        session.add(cat)
        session.commit()
        return cat
    except IntegrityError:
        session.rollback()
        return (session.query(Category)
                .filter(func.lower(Category.name) == name.lower())
                .first())

def _ensure_subcategory(session, category: Category, name: str) -> Subcategory:
    sub = (session.query(Subcategory)
           .filter(func.lower(Subcategory.name) == name.lower(),
                   Subcategory.category_id == category.id)
           .first())
    if sub:
        return sub
    try:
        sub = Subcategory(name=name.lower(),
                          category_id=category.id,
                          description=AUTO_DESC)
        session.add(sub)
        session.commit()
        return sub
    except IntegrityError:
        session.rollback()
        return (session.query(Subcategory)
                .filter(func.lower(Subcategory.name) == name.lower(),
                        Subcategory.category_id == category.id)
                .first())

def ensure_gd_namespace(category_name: str, subcategory_name: str, short_key: str,
                        auto_create: bool = True) -> str:
    """
    Returns 'gd.<category>.<subcategory>.<short_key>'.
    If auto_create=True (default), will create missing Category/Subcategory rows.
    Will NOT auto-create if category/subcategory are 'uncategorized'/'unknown' to avoid polluting taxonomy.
    """
    category_name = (category_name or "").strip().lower()
    subcategory_name = (subcategory_name or "").strip().lower()
    short_key = (short_key or "").strip().lower()

    # guard against trash taxonomy
    if category_name in {"", "uncategorized", "unknown"} or \
       subcategory_name in {"", "unknown"}:
        return f"gd.{category_name or 'uncategorized'}.{subcategory_name or 'unknown'}.{short_key or 'unknown'}"

    with SessionLocal() as session:
        cat = (session.query(Category)
               .filter(func.lower(Category.name) == category_name)
               .first())
        sub = None
        if not cat and auto_create:
            cat = _ensure_category(session, category_name)
        if cat:
            sub = (session.query(Subcategory)
                   .filter(func.lower(Subcategory.name) == subcategory_name,
                           Subcategory.category_id == cat.id)
                   .first())
            if not sub and auto_create:
                sub = _ensure_subcategory(session, cat, subcategory_name)

        # If still missing anything, fall back—but keep gd.* shape.
        if not cat or not sub:
            return f"gd.{category_name}.{subcategory_name}.{short_key}"

        return f"gd.{cat.name}.{sub.name}.{short_key.lower()}"
