from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import SchemaMigration


MIGRATIONS = (
    "20260826_01_fastapi_m1",
    "20260828_01_lanseir_product_spine",
)


def run_migrations(engine) -> list[str]:
    """Apply additive, idempotent schema migrations and record their versions.

    M2 adds tables and indexes only; it does not rewrite or delete M1 data.
    Future destructive or column-altering changes require explicit migration SQL.
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
