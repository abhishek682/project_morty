import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.db import Base, engine, get_db
from app.observability.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.observability.tracing import setup_tracing
from app.schemas import PaginatedResponse
from app.services.character_service import list_characters, get_redis

app = FastAPI(title="Rick and Morty API", version="1.0.0")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    storage_uri=settings.rate_limit_storage_uri or settings.redis_url,
)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(duration)
    return response


@app.on_event("startup")
def on_startup():
    if settings.log_file:
        logging.basicConfig(
            filename=settings.log_file,
            level=settings.log_level.upper(),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    Base.metadata.create_all(bind=engine)
    setup_tracing(app)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthcheck")
def healthcheck(db: Session = Depends(get_db)):
    health = {"database": "ok", "cache": "ok"}
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        health["database"] = "error"
    try:
        get_redis().ping()
    except Exception:
        health["cache"] = "error"

    status_code = 200 if all(value == "ok" for value in health.values()) else 503
    return JSONResponse(status_code=status_code, content=health)


@app.get("/characters", response_model=PaginatedResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def characters(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("id"),
    db: Session = Depends(get_db),
):
    try:
        total, items = list_characters(db, page, limit, sort)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Upstream dependency failure") from exc
    return {"page": page, "limit": limit, "total": total, "items": items}
