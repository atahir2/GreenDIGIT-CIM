from cloud_metrics.utils.config import SessionLocal
from cloud_metrics.services.standards_registry import attach_standard, ensure_seed_standards
from cloud_metrics.models.metric_definition import MetricDefinition
from sqlalchemy import func

def main():
    ensure_seed_standards()

    # created = updated = skipped = 0
    # with SessionLocal() as s:
    #     rows = s.query(MetricDefinition.unified_key).all()
    # total = len(rows)
    # print(f"[standards-backfill] scanning {total} metric_definitions...")
    #
    # for (uk,) in rows:
    #     try:
    #         # before = (created, updated)
    #         attach_standard(uk)
    #         # attach_standard() is idempotent; we don’t know exactly if it created/updated without another query.
    #         # If you want precise counts, you can instrument attach_standard to return an action string.
    #     except Exception as e:
    #         # skipped += 1
    #         print(f"  skip {uk}: {e}")

    uks = ["gd.performance.cpu.utilization", "gd.performance.memory.usage"]
    with SessionLocal() as s:
        for uk in uks:
            exists = s.query(MetricDefinition).filter(MetricDefinition.unified_key == uk).first()
            if exists:
                attach_standard(uk)


    print("backfill done.")

if __name__ == "__main__":
    main()
