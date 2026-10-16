from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .metrics import register_inventory_collector
from .routers import items, loans, stats

# Schema is owned by Alembic (run as a separate migrate step / Helm hook Job),
# so the API never creates tables on startup.
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Track lab equipment, who borrowed it, and when it is due back.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

Instrumentator(excluded_handlers=["/health", "/ready", "/metrics"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)
register_inventory_collector()

app.include_router(stats.router)
app.include_router(items.router)
app.include_router(loans.router)


@app.get("/", tags=["meta"])
def root():
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health():
    """Liveness: the process is up. Deliberately does not touch the database."""
    return {"status": "UP"}


@app.get("/ready", tags=["meta"])
def ready(db: Session = Depends(get_db)):
    """Readiness: the database is reachable and migrations have created our tables."""
    try:
        db.execute(text("SELECT 1 FROM items LIMIT 1"))
    except Exception as exc:
        return JSONResponse(status_code=503, content={"status": "NOT_READY", "reason": type(exc).__name__})
    return {"status": "READY"}
