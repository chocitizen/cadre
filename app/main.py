from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.product import router as product_router
from app.api.routes import router as core_router
from app.api.gateway import router as gateway_router
from app.core.config import get_settings
from app.core.middleware import RateLimitMiddleware, RequestBodyLimitMiddleware, RequestContextMiddleware
from app.db.migrations import run_migrations
from app.db.session import engine
from app.services.seed import seed_doctrine, seed_product


settings = get_settings()
web_root = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.models import entities  # noqa: F401

    run_migrations(engine)
    with Session(engine) as db:
        seed_doctrine(db)
        seed_product(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.5.0",
    description="LANSEIR product experience with the CADRE operating system",
    docs_url=None if settings.env == "production" else "/docs",
    redoc_url=None if settings.env == "production" else "/redoc",
    openapi_url=None if settings.env == "production" else "/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(RequestBodyLimitMiddleware, max_bytes=settings.max_request_body_bytes)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.auth_rate_limit_per_minute)
app.add_middleware(RequestContextMiddleware, environment=settings.env)
app.include_router(core_router, prefix=settings.api_prefix)
app.include_router(product_router, prefix=settings.api_prefix)
app.include_router(gateway_router, prefix=settings.api_prefix)
app.mount("/static", StaticFiles(directory=web_root / "static"), name="static")


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("cadre.error").exception(
        "unhandled request error",
        extra={"request_id": getattr(request.state, "request_id", None), "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "The request could not be completed", "request_id": getattr(request.state, "request_id", None)},
    )


def product_shell() -> FileResponse:
    return FileResponse(web_root / "index.html")


@app.get("/", include_in_schema=False)
@app.get("/app", include_in_schema=False)
@app.get("/privacy", include_in_schema=False)
@app.get("/terms", include_in_schema=False)
@app.get("/support", include_in_schema=False)
def root() -> FileResponse:
    return product_shell()


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(web_root / "static" / "favicon.svg", media_type="image/svg+xml")


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok", "system": "LANSEIR", "release": settings.release_id}


@app.get("/{full_path:path}", include_in_schema=False)
def not_found(full_path: str):
    if full_path.startswith(("api/", "static/")):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return FileResponse(web_root / "index.html", status_code=404)
