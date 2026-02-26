from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Character
from app.services import character_service


def test_list_characters_empty_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def noop_sync(_db):
        return None

    monkeypatch.setattr(character_service, "sync_characters_if_needed", noop_sync)
    monkeypatch.setattr(character_service, "get_redis", lambda: DummyRedis())

    db = TestingSessionLocal()
    total, items = character_service.list_characters(db, page=1, limit=10, sort="id")
    assert total == 0
    assert items == []


def test_list_characters_sort_by_name(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(character_service, "sync_characters_if_needed", lambda _db: None)
    monkeypatch.setattr(character_service, "get_redis", lambda: DummyRedis())

    db = TestingSessionLocal()
    db.add(Character(id=1, name="Beth", status="Alive", species="Human", origin_name="Earth (C-137)"))
    db.add(Character(id=2, name="Arthur", status="Alive", species="Human", origin_name="Earth (Replacement)"))
    db.commit()

    total, items = character_service.list_characters(db, page=1, limit=10, sort="name")
    assert total == 2
    assert items[0]["name"] == "Arthur"


class DummyRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def setex(self, key, ttl, value):
        self.store[key] = value

    def ping(self):
        return True
