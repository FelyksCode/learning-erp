from fastapi.testclient import TestClient

from app.main import app


def expect(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    assert cond, label


def login(c):
    r = c.post("/api/auth/token", data={"username": "admin", "password": "admin"})
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

with TestClient(app) as c:
    login(c)
    r = c.post("/api/catalog/partners", json={"name": "Acme Drinks", "partner_type": "supplier"})
    supplier_id = r.json()["id"]
    r = c.post("/api/catalog/categories", json={"name": "Snacks"})
    cat_id = r.json()["id"]

    p1 = c.post(
        "/api/products",
        json={"sku": "CHIPS-50", "name": "Chips 50g", "category_id": cat_id, "unit_cost": "0.30", "sale_price": "0.90"},
    ).json()
    p2 = c.post(
        "/api/products",
        json={"sku": "WATER-500", "name": "Water 500ml", "category_id": cat_id, "unit_cost": "0.10", "sale_price": "0.35"},
    ).json()

    r = c.post(
        "/api/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "reference": "PO-ACME-001",
            "lines": [
                {"product_id": p1["id"], "quantity": 200},
                {"product_id": p2["id"], "quantity": 300, "unit_cost": "0.08"},
            ],
        },
    )
    expect(r.status_code == 201, f"create draft PO ({r.status_code} {r.text[:120]})")
    po = r.json()
    po_id = po["id"]
    expect(po["status"] == "draft", "starts as draft")
    expect(str(po["lines"][0]["unit_cost"]) in ("0.30",), "line cost defaults to product cost")
    expect(str(po["total_cost"]) in ("84.00", "84.0000"), f"total 200*0.30 + 300*0.08 = {po['total_cost']}")

    r = c.post(f"/api/purchase-orders/{po_id}/receive", json={})
    expect(r.status_code == 400, "receive before ordering rejected")

    r = c.post(f"/api/purchase-orders/{po_id}/order")
    expect(r.status_code == 200 and r.json()["status"] == "ordered", "mark ordered")

    r = c.post(f"/api/purchase-orders/{po_id}/receive", json={
        "location_code": "SHOP",
        "lines": [{"line_id": po["lines"][0]["id"], "quantity": 150}],
    })
    expect(r.status_code == 200, f"partial receive 150/200 chips ({r.status_code} {r.text[:120]})")
    got = r.json()["lines"][0]
    expect(str(got["quantity_received"]) in ("150", "150.00"), f"chips received tracked: {got['quantity_received']}")

    on_hand_chips = c.get(f"/api/products/{p1['id']}").json()["on_hand"]
    expect(str(on_hand_chips) in ("150", "150.00"), f"ledger updated by receipt: {on_hand_chips}")

    r = c.post(f"/api/purchase-orders/{po_id}/receive", json={
        "location_code": "SHOP",
        "lines": [
            {"line_id": po["lines"][0]["id"], "quantity": 51},
        ],
    })
    expect(r.status_code == 400, "over-receipt rejected (51 > remaining 50)")

    r = c.post(f"/api/purchase-orders/{po_id}/cancel")
    expect(r.status_code == 400, "cancel blocked after partial receipt")

    r = c.post(f"/api/purchase-orders/{po_id}/receive", json={})
    expect(r.status_code == 200 and r.json()["status"] == "received", "receive remainder -> status received")

    on_hand_water = c.get(f"/api/products/{p2['id']}").json()["on_hand"]
    expect(str(on_hand_water) in ("300", "300.00"), f"water fully received into SHOP: {on_hand_water}")

    moves = c.get("/api/stock-moves", params={"product_id": p1["id"]}).json()
    refs = [m["reference"] for m in moves]
    expect(all(ref and ref.startswith("PO-") for ref in refs), f"receipt moves carry PO reference: {refs}")
    costs = {str(m["unit_cost"]) for m in moves}
    expect("0.3" in costs or "0.30" in costs, f"moves snapshot unit_cost from PO line: {costs}")

    r = c.get("/api/purchase-orders", params={"status": "received"})
    expect(any(x["id"] == po_id for x in r.json()), "filter by status=received works")

    r = c.post("/api/purchase-orders", json={"supplier_id": supplier_id, "lines": [{"product_id": p1["id"], "quantity": 10}]})
    d2 = r.json()["id"]
    c.post(f"/api/purchase-orders/{d2}/order")
    r = c.post(f"/api/purchase-orders/{d2}/cancel")
    expect(r.status_code == 200 and r.json()["status"] == "cancelled", "cancel clean ordered PO ok")

print("\nAll M2 smoke checks passed.")
