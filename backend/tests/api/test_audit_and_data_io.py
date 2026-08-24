import io

import pytest

pytestmark = pytest.mark.api


def test_product_mutations_leave_an_audit_trail(client, make_product):
    product = make_product("AUD-1")
    client.patch(f"/api/products/{product['id']}", json={"sale_price": "2.50"})
    client.delete(f"/api/products/{product['id']}")

    audit = client.get("/api/audit").json()
    entries = [(e["action"], e["entity"], e["entity_id"], e["username"]) for e in audit["items"]]

    assert ("create", "product", product["id"], "admin") in entries
    assert ("update", "product", product["id"], "admin") in entries
    assert ("deactivate", "product", product["id"], "admin") in entries
    ids_in_order = [e["id"] for e in audit["items"]]
    assert ids_in_order == sorted(ids_in_order, reverse=True)


def test_products_csv_export_and_reimport_roundtrip(client, make_product):
    make_product("CSV-1", unit_cost="0.75", sale_price="1.80")

    exported = client.get("/api/export/products.csv").text
    header, *rows = exported.strip().splitlines()

    assert header == "sku,name,category_id,unit_cost,sale_price,on_hand,avg_daily_sales_30d"
    assert any(row.startswith("CSV-1") for row in rows)

    updated_csv = "sku,name,unit_cost,sale_price\nCSV-1,Updated name,0.90,2.00\n"
    r = client.post(
        "/api/import/products",
        files={"file": ("products.csv", io.BytesIO(updated_csv.encode()), "text/csv")},
    )

    assert r.status_code == 200
    assert r.json()["updated"] == 1

    stored = next(p for p in client.get("/api/products").json() if p["sku"] == "CSV-1")
    assert stored["name"] == "Updated name"
    assert str(stored["unit_cost"]) in ("0.9", "0.90")


def test_non_csv_upload_is_rejected(client):
    r = client.post(
        "/api/import/products",
        files={"file": ("data.txt", io.BytesIO(b"nope"), "text/plain")},
    )

    assert r.status_code == 400
