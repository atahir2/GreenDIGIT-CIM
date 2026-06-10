# cloud_metrics/services/insert_file_upload_log.py

from sqlalchemy.exc import IntegrityError
from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.models.upload_log import FileUploadLog

def insert_file_upload_log(filename: str, datacenter_id: int, uploaded_by: str = None):
    session = SessionLocal()
    try:
        log = FileUploadLog(
            filename=filename,
            datacenter_id=datacenter_id,
            uploaded_by=uploaded_by
        )
        session.add(log)
        session.commit()
        print(f"✅ File upload log for '{filename}' inserted successfully.")
    except IntegrityError:
        session.rollback()
        print(f"⚠️ Duplicate entry or constraint issue for file '{filename}'.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error inserting file upload log: {e}")
    finally:
        session.close()
