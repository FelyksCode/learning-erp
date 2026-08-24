from fastapi.testclient import TestClient

from app.main import app

def login(c):
    r = c.post("/api/auth/token", data={"username": "admin", "password": "admin"})
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

with TestClient(app) as c:
    login(c)
    r = c.get("/api/health")
    print("health:", r.status_code, r.json())

    r = c.post("/api/catalog/categories", json={"name": "Beverages"})
    print("category:", r.status_code)
    cat_id = r.json()["id"]

    r = c.post(
        "/api/products",
        json={
            "sku": "COLA-330",
            "name": "Cola 330ml",
            "category_id": cat_id,
            "unit_cost": "0.40",
            "sale_price": "1.00",
            "reorder_enabled": True,
        },
    )
    print("product:", r.status_code)
    pid = r.json()["id"]

    r = c.post(
        "/api/stock-moves",
        json={
            "product_id": pid,
            "to_location_code": "SHOP",
            "quantity": 100,
            "unit_cost": "0.40",
            "reference": "PO-1",
        },
    )
    print("receive:", r.status_code)

    r = c.post(
        "/api/stock-moves",
        json={"product_id": pid, "from_location_code": "SHOP", "quantity": 35, "reference": "SALE-1"},
    )
    print("sale:", r.status_code)

    r = c.post(
        "/api/stock-moves",
        json={
            "product_id": pid,
            "from_location_code": "SHOP",
            "quantity": 2,
            "to_location_code": "LOSS",
            "reference": "damaged",
        },
    )
    print("loss:", r.status_code)

    r = c.get(f"/api/products/{pid}")
    print("on_hand:", r.status_code, "=", r.json()["on_hand"], "(expect 63)")

    r = c.post(
        "/api/stock-moves",
        json={
            "product_id": pid,
            "to_location_code": "STORAGE",
            "quantity": 10,
            "unit_cost": "0.40",
            "reference": "PO-2",
        },
    )
    print("implicit supplier receive:", r.status_code)

    r = c.post(
        "/api/stock-moves",
        json={"product_id": pid, "from_location_code": "SUPPLIER", "to_location_code": "LOSS", "quantity": 5},
    )
    print("invalid direction rejected:", r.status_code, "-", r.json().get("detail"))

    r = c.post("/api/stock-moves", json={"product_id": pid, "quantity": 5})
    print("no-direction move rejected:", r.status_code, "-", r.json().get("detail"))
