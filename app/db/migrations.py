from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import SchemaMigration


MIGRATIONS = (
    "20260826_01_fastapi_m1",
    "20260828_01_lanseir_product_spine",
    "20260828_02_mission_execution_and_provenance",
)


def run_migrations(engine) -> list[str]:
    """Apply additive, idempotent schema creation and record its version.

    The current release adds only tables and indexes. Future destructive or
    column-altering work requires an explicit migration and rollback plan.
    """
    Base.metadata.create_all(bind=engine)
    applied: list[str] = []
    with Session(engine) as db:
        for version in MIGRATIONS:
            if db.scalar(select(SchemaMigration).where(SchemaMigration.version == version)) is None:
                db.add(SchemaMigration(version=version))
                applied.append(version)
        db.commit()
    return applied
