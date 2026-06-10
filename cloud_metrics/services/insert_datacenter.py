# cloud_metrics/services/insert_datacenter.py

from sqlalchemy.exc import IntegrityError
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.datacenter import Datacenter

def insert_datacenter(name: str, location: str = None, provider: str = None):
    session = SessionLocal()
    try:
        dc = Datacenter(name=name, location=location, provider=provider)
        session.add(dc)
        session.commit()
        print(f"✅ Datacenter '{name}' inserted successfully.")
    except IntegrityError:
        session.rollback()
        print(f"⚠️ Datacenter '{name}' already exists.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error inserting datacenter: {e}")
    finally:
        session.close()

def get_or_create_datacenter_id(name: str) -> int:
    with SessionLocal() as s:
        dc = s.query(Datacenter).filter(Datacenter.name == name).first()
        if dc:
            return dc.id
        dc = Datacenter(name=name)
        s.add(dc)
        s.commit()
        return dc.id