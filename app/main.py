from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.api.routes import router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.services.seed import seed_doctrine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.models import entities  # noqa: F401
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_doctrine(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="CADRE Milestone 1 — Sovereign Core Foundation",
    lifespan=lifespan,
)
app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict:
    return {
        "system": "CADRE",
        "milestone": "M1 — Sovereign Core Foundation",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }
