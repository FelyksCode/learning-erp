from fastapi.testclient import TestClient

from app.main import app


def expect(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    assert cond, label


with TestClient(app) as c:
    r = c.get("/api/health")
    expect(r.status_code == 200, "health stays open")

    r = c.get("/api/products")
    expect(r.status_code == 401, "products protected: no token -> 401")

    r = c.post("/api/auth/token", data={"username": "admin", "password": "wrong"})
    expect(r.status_code == 401, "wrong password -> 401")

    r = c.post("/api/auth/token", data={"username": "admin", "password": "admin"})
    expect(r.status_code == 200 and r.json()["token_type"] == "bearer", "admin login ok")
    admin_token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {admin_token}"}

    r = c.get("/api/auth/me", headers=auth)
    expect(r.status_code == 200 and r.json()["username"] == "admin" and r.json()["role"] == "admin",
           "/me returns admin identity")

    r = c.get("/api/products", headers=auth)
    expect(r.status_code == 200, "products accessible with token")

    r = c.post("/api/catalog/partners", headers=auth,
               json={"name": "Staff Supplier", "partner_type": "supplier"})
    supplier_id = r.json()["id"]

    r = c.post("/api/auth/users", headers=auth,
               json={"username": "staff1", "password": "staffpass", "role": "staff"})
    expect(r.status_code == 201, "admin creates staff user")

    r = c.post("/api/auth/users", json={"username": "x2", "password": "abcdef", "role": "staff"})
    expect(r.status_code in (401,), "user creation requires token")

    staff_auth = {}
    r = c.post("/api/auth/token", data={"username": "staff1", "password": "staffpass"})
    expect(r.status_code == 200, "staff login ok")
    staff_token = r.json()["access_token"]
    staff_auth = {"Authorization": f"Bearer {staff_token}"}

    r = c.get("/api/auth/users", headers=staff_auth)
    expect(r.status_code == 403, "staff forbidden from user list (403)")

    r = c.get("/api/audit", headers=staff_auth)
    expect(r.status_code == 403, "staff forbidden from audit log (403)")

    r = c.post("/api/stock-moves", headers=staff_auth,
               json={"product_id": 999999, "to_location_code": "SHOP", "quantity": 1})
    expect(r.status_code in (400, 404), "staff may post moves (validation error, not 403)")

    r = c.post("/api/products", headers=auth,
               json={"sku": "AUDIT-1", "name": "Audit probe", "unit_cost": "1", "sale_price": "2"})
    expect(r.status_code == 201, "product created for audit check")
    product_id = r.json()["id"]
    c.patch(f"/api/products/{product_id}", headers=auth, json={"sale_price": "2.50"})
    c.delete(f"/api/products/{product_id}", headers=auth)

    r = c.get("/api/audit", headers=auth)
    expect(r.status_code == 200 and r.json()["total"] >= 3, f"audit has entries ({r.json()['total']})")
    items = r.json()["items"]
    actions = {item["action"] for item in items}
    expect({"create", "update", "deactivate"} <= actions, f"product lifecycle audited: {sorted(actions)}")
    user_events = [i for i in items if i["entity"] == "user"]
    expect(any(i["action"] == "create" for i in user_events), "user creation audited")
    usernames = {item["username"] for item in items}
    expect(usernames <= {"admin"}, f"audit usernames tracked: {usernames}")

    r = c.patch("/api/auth/users/2", headers=auth, json={"is_active": False})
    expect(r.status_code == 200 and r.json()["is_active"] is False, "admin deactivates staff")

    r = c.post("/api/auth/token", data={"username": "staff1", "password": "staffpass"})
    expect(r.status_code == 401, "deactivated user cannot login")

    bad = {"Authorization": "Bearer not.a.jwt"}
    r = c.get("/api/products", headers=bad)
    expect(r.status_code == 401, "garbage token rejected")

print("\nAll M5 smoke checks passed.")
