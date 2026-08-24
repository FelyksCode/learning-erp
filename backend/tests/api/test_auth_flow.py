import pytest

pytestmark = pytest.mark.api


def test_health_is_open_even_without_a_token(raw_client):
    assert raw_client.get("/api/health").status_code == 200


def test_business_endpoints_reject_anonymous_callers(raw_client):
    r = raw_client.get("/api/products")

    assert r.status_code == 401


def test_garbage_tokens_are_rejected(raw_client):
    r = raw_client.get("/api/products", headers={"Authorization": "Bearer not.a.real.jwt"})

    assert r.status_code == 401


def test_login_rejects_wrong_password(raw_client):
    r = raw_client.post("/api/auth/token", data={"username": "admin", "password": "nope"})

    assert r.status_code == 401


def test_me_identifies_the_signed_in_admin(client):
    r = client.get("/api/auth/me")

    body = r.json()
    assert r.status_code == 200
    assert body["username"] == "admin"
    assert body["role"] == "admin"


def test_staff_cannot_manage_users_or_read_audit(staff_client):
    assert staff_client.get("/api/auth/users").status_code == 403
    assert staff_client.get("/api/audit").status_code == 403


def test_staff_can_do_their_day_job(staff_client, make_product):
    product = make_product("STAFF-1")

    r = staff_client.get(f"/api/products/{product['id']}")

    assert r.status_code == 200
    assert r.json()["on_hand"] == "0.00"


def test_duplicate_username_is_rejected(client):
    payload = {"username": "dupe", "password": "abcdef", "role": "staff"}
    assert client.post("/api/auth/users", json=payload).status_code == 201

    r = client.post("/api/auth/users", json=payload)

    assert r.status_code == 409


def test_deactivated_user_cannot_log_in(client, raw_client):
    r = client.post(
        "/api/auth/users",
        json={"username": "temp", "password": "abcdef", "role": "staff"},
    )
    user_id = r.json()["id"]
    client.patch(f"/api/auth/users/{user_id}", json={"is_active": False})

    login = raw_client.post("/api/auth/token", data={"username": "temp", "password": "abcdef"})

    assert login.status_code == 401
