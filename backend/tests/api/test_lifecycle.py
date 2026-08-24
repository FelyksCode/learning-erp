from decimal import Decimal

import pytest

pytestmark = pytest.mark.integration


def _create_supplier(client, name="Acme Wholesale"):
    r = client.post("/api/catalog/partners", json={"name": name, "partner_type": "supplier"})
    assert r.status_code == 201, r.text
    return r.json()


def test_full_flow_purchase_receive_sell_analytics(client, make_product):
    supplier = _create_supplier(client)
    product = make_product("FLOW-1", unit_cost="0.40", sale_price="1.00")

    r = client.post(
        "/api/purchase-orders",
        json={"supplier_id": supplier["id"], "reference": "PO-1",
              "lines": [{"product_id": product["id"], "quantity": 100}]},
    )
    assert r.status_code == 201, r.text
    po = r.json()

    assert client.post(f"/api/purchase-orders/{po['id']}/receive", json={}).status_code == 400

    assert client.post(f"/api/purchase-orders/{po['id']}/order").status_code == 200

    r = client.post(f"/api/purchase-orders/{po['id']}/receive", json={})
    assert r.status_code == 200 and r.json()["status"] == "received"

    r = client.get(f"/api/products/{product['id']}")
    assert r.json()["on_hand"] == "100.00"

    r = client.post("/api/sales", json={"lines": [{"product_id": product["id"], "quantity": 30}]})
    assert r.status_code == 201
    assert r.json()["total_revenue"] in ("30.0", "30.00", "30.0000")

    r = client.get(f"/api/products/{product['id']}")
    assert r.json()["on_hand"] == "70.00"

    restock = {row["sku"]: row for row in client.get("/api/analytics/restock").json()}
    assert Decimal(restock["FLOW-1"]["avg_daily_sales"]) > 0

    overview = client.get("/api/analytics/overview").json()
    assert Decimal(str(overview["revenue_30d"])) == Decimal("30.00")


def test_over_receipt_is_rejected(client, make_product):
    supplier = _create_supplier(client, "Over Receipt Co")
    product = make_product("OVER-1")
    po_id = client.post(
        "/api/purchase-orders",
        json={"supplier_id": supplier["id"],
              "lines": [{"product_id": product["id"], "quantity": 10}]},
    ).json()["id"]
    client.post(f"/api/purchase-orders/{po_id}/order")
    line_id = client.get(f"/api/purchase-orders/{po_id}").json()["lines"][0]["id"]

    r = client.post(
        f"/api/purchase-orders/{po_id}/receive",
        json={"lines": [{"line_id": line_id, "quantity": 11}]},
    )

    assert r.status_code == 400
    assert "remaining" in r.json()["detail"]


def test_cannot_sell_more_than_on_hand(client, make_product):
    product = make_product("NEG-1")

    r = client.post("/api/sales", json={"lines": [{"product_id": product["id"], "quantity": 5}]})

    assert r.status_code == 400
    assert "Insufficient stock" in r.json()["detail"]


def test_sale_price_snapshot_survives_later_price_edits(client, make_product):
    product = make_product("SNAP-1", sale_price="2.00")
    client.post(
        "/api/stock-moves",
        json={"product_id": product["id"], "to_location_code": "SHOP", "quantity": 50,
              "unit_cost": "1.00", "reference": "OPEN"},
    )
    client.post("/api/sales", json={"lines": [{"product_id": product["id"], "quantity": 1}]})
    client.patch(f"/api/products/{product['id']}", json={"sale_price": "9.99"})
    client.post("/api/sales", json={"lines": [{"product_id": product["id"], "quantity": 1}]})

    sales = client.get("/api/sales").json()
    prices = sorted(
        str(line["unit_price"]) for s in sales
        for line in s["lines"] if line["product_id"] == product["id"]
    )

    assert prices == ["2.00", "9.99"] or prices == ["2.0", "9.99"]
