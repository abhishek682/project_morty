import json
import time
from typing import Tuple

import redis
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Character
from app.observability.metrics import CACHE_HITS, CACHE_MISSES
from app.services.rick_and_morty import fetch_filtered_characters


_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _last_sync_key() -> str:
    return "characters:last_sync"


def _cache_key(page: int, limit: int, sort: str) -> str:
    return f"characters:{page}:{limit}:{sort}"


def _should_sync(redis_client) -> bool:
    last_sync = redis_client.get(_last_sync_key())
    if not last_sync:
        return True
    return (time.time() - float(last_sync)) > settings.sync_interval_seconds


def sync_characters_if_needed(db: Session) -> None:
    try:
        redis_client = get_redis()
    except Exception:
        redis_client = None

    if redis_client and not _should_sync(redis_client):
        return
    if redis_client is None:
        existing = db.execute(
            select(func.count()).select_from(Character).where(Character.origin_name.ilike("Earth%"))
        ).scalar_one()
        if existing > 0:
            return

    for character in fetch_filtered_characters():
        statement = insert(Character).values(**character)
        update_fields = {k: statement.excluded[k] for k in character.keys() if k != "id"}
        statement = statement.on_conflict_do_update(index_elements=["id"], set_=update_fields)
        db.execute(statement)
    db.commit()
    if redis_client:
        redis_client.set(_last_sync_key(), str(time.time()))


def _serialize_character(item: Character) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "status": item.status,
        "species": item.species,
        "origin_name": item.origin_name,
        "origin_url": item.origin_url,
        "image": item.image,
    }


def list_characters(db: Session, page: int, limit: int, sort: str) -> Tuple[int, list[dict]]:
    if sort not in {"id", "name"}:
        raise ValueError("Unsupported sort field")

    cache_key = _cache_key(page, limit, sort)
    redis_client = None
    try:
        redis_client = get_redis()
        cached = redis_client.get(cache_key)
        if cached:
            CACHE_HITS.labels(cache="characters").inc()
            payload = json.loads(cached)
            return payload["total"], payload["items"]
    except Exception:
        redis_client = None

    CACHE_MISSES.labels(cache="characters").inc()
    sync_characters_if_needed(db)

    query = select(Character).where(Character.origin_name.ilike("Earth%"))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    query = query.order_by(getattr(Character, sort)).offset((page - 1) * limit).limit(limit)
    items = [row[0] for row in db.execute(query).all()]
    serialized = [_serialize_character(item) for item in items]

    if redis_client:
        redis_client.setex(
            cache_key,
            settings.cache_ttl_seconds,
            json.dumps({"total": total, "items": serialized}),
        )
    return total, serialized
