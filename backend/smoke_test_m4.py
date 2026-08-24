import io

from fastapi.testclient import TestClient

from app.main import app


def expect(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    assert cond, label


CSV = """sku,name,category,unit_cost,sale_price
MUG-11, Ceramic mug 330ml, Drinkware, 0.80, 2.50
NOTE-A5, Notebook A5 dotted, Stationery, 0.60, 1.90
"""

def login(c):
    r = c.post("/api/auth/token", data={"username": "admin", "password": "admin"})
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

with TestClient(app) as c:
    login(c)
    r = c.get("/api/ai/insights")
    body = r.json()
    expect(r.status_code == 200 and body["enabled"] is False and "AI_ENABLED" in body["reason"],
           f"AI disabled by default with setup hint: {body['reason'][:60]}...")

    r = c.post("/api/import/products", files={"file": ("products.csv", io.BytesIO(CSV.encode()), "text/csv")})
    expect(r.status_code == 200 and r.json() == {"created": 2, "updated": 0, "skipped": 0},
           f"import creates 2 products ({r.text[:120]})")

    mug = c.get("/api/products", params={"q": "MUG"}).json()[0]
    expect(str(mug["unit_cost"]) in ("0.8", "0.80") and str(mug["sale_price"]) in ("2.5", "2.50"),
           f"imported costs/prices parsed ({mug['unit_cost']}, {mug['sale_price']})")

    r = c.post("/api/import/products", files={"file": ("products.csv", io.BytesIO(
        b"sku,name,unit_cost,sale_price\nMUG-11,Ceramic mug 330ml large,1.00,3.00\n") , "text/csv")})
    expect(r.status_code == 200 and r.json()["updated"] == 1, f"re-import upserts by SKU ({r.text[:100]})")
    mug = c.get(f"/api/products/{mug['id']}").json()
    expect(mug["name"] == "Ceramic mug 330ml large" and str(mug["unit_cost"]) in ("1.0", "1.00"),
           f"upsert applied changes ({mug['name']}, {mug['unit_cost']})")

    r = c.post("/api/stock-moves", json={"product_id": mug["id"], "to_location_code": "SHOP",
                                         "quantity": 40, "unit_cost": "1.00", "reference": "OPEN"})
    expect(r.status_code == 201, "stock in for export test")
    c.post("/api/sales", json={"lines": [{"product_id": mug["id"], "quantity": 3}]})

    r = c.get("/api/export/products.csv")
    lines = r.text.strip().splitlines()
    expect(lines[0].startswith("sku,name,category_id"), f"products header ok: {lines[0]}")
    mug_row = next(l for l in lines if l.startswith("MUG-11"))
    expect(",37.00," in mug_row, f"on_hand computed in export (40-3): {mug_row}")

    r = c.get("/api/export/sales.csv")
    slines = r.text.strip().splitlines()
    expect(slines[0] == "sold_at,sale_id,reference,sku,quantity,unit_price,line_revenue", "sales header ok")
    expect(len(slines) == 2 and "MUG-11" in slines[1] and "9.00" in slines[1],
           f"sales row w/ snapshot price 3*3.00: {slines[1]}")

    r = c.post("/api/import/products", files={"file": ("bad.txt", io.BytesIO(b"x,y\n1,2"), "text/plain")})
    expect(r.status_code == 400, "non-csv upload rejected")

print("\nAll M4 smoke checks passed.")
