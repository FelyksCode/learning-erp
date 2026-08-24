import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import get_db
from app.main import app, seed_admin_user, seed_locations
from app.models.base import Base

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test starts from the same clean, fully-seeded database.

    Isolation is the #1 rule of test design: no test may depend on another
    test having run before it. Dropping + recreating the in-memory schema is
    fast (<50ms) and guarantees identical starting state for every test.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_locations(db)
        seed_admin_user(db)
        db.commit()
    yield


@pytest.fixture
def db_session():
    """Direct ORM access for unit-style tests of service functions."""
    with TestingSessionLocal() as session:
        yield session


def _override_db():
    def override_get_db():
        with TestingSessionLocal() as session:
            yield session

    return override_get_db


@pytest.fixture
def raw_client():
    """HTTP client with NO authentication header — for testing auth guards."""
    app.dependency_overrides[get_db] = _override_db()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client(raw_client):
    """HTTP client authenticated as the seeded admin."""
    r = raw_client.post("/api/auth/token", data={"username": "admin", "password": "admin"})
    assert r.status_code == 200, r.text
    raw_client.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return raw_client


@pytest.fixture
def staff_client(raw_client):
    """HTTP client authenticated as a freshly created staff user."""
    r = raw_client.post("/api/auth/token", data={"username": "admin", "password": "admin"})
    admin = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = raw_client.post(
        "/api/auth/users",
        headers=admin,
        json={"username": "staffer", "password": "staffpass", "role": "staff"},
    )
    assert r.status_code == 201, r.text
    r = raw_client.post("/api/auth/token", data={"username": "staffer", "password": "staffpass"})
    assert r.status_code == 200, r.text
    raw_client.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return raw_client


@pytest.fixture
def make_product(client):
    """Factory fixture: tests call it to create products with sensible defaults.

    Factory-as-fixture keeps the arrange step short and makes each test's
    intent visible — only non-default arguments appear in the test body.
    """

    def _make(sku: str, **overrides):
        payload = {"sku": sku, "name": f"Product {sku}", "unit_cost": "1.00", "sale_price": "2.00"}
        payload.update(overrides)
        r = client.post("/api/products", json=payload)
        assert r.status_code == 201, r.text
        return r.json()

    return _make
