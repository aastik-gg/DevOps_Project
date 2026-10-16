import os

# Tests never touch Postgres: point settings at SQLite before the app is imported.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import db as db_module
from app.db import Base, get_db
from app.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
# The /metrics collector opens its own sessions; send those to the test DB too.
db_module.SessionLocal = TestingSession


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_item(client):
    def _make(**overrides):
        payload = {"name": "Oscilloscope", "category": "Measurement", "asset_tag": "LAB-001"} | overrides
        response = client.post("/api/items", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def db_session():
    with TestingSession() as session:
        yield session
