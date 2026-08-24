from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app


def expect(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    assert cond, label


BACKDATE_DAYS = 10


def backdate_last_sale(db_path: str):
    """Rewrite the newest sale's sold_at to N days ago so velocity math is testable."""
    import sqlite3

    con = sqlite3.connect(db_path)
    old = (datetime.now(timezone.utc) - timedelta(days=BACKDATE_DAYS)).isoformat()
    con.execute("UPDATE sales SET sold_at = ? WHERE id = (SELECT MAX(id) FROM sales)", (old,))
    con.commit()
    con.close()


def login(c):
    r = c.post("/api/auth/token", data={"username": "admin", "password": "admin"})
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

with TestClient(app) as c:
    login(c)
    p = c.post(
        "/api/products",
        json={"sku": "SODA-1L", "name": "Soda 1L", "unit_cost": "0.50", "sale_price": "1.20",
              "reorder_enabled": True, "lead_time_days": 5, "safety_stock": 10},
    ).json()

    r = c.post("/api/purchase-orders", json={
        "supplier_id": c.post("/api/catalog/partners", json={"name": "SodaCo", "partner_type": "supplier"}).json()["id"],
        "lines": [{"product_id": p["id"], "quantity": 100}],
    })
    po_id = r.json()["id"]
    c.post(f"/api/purchase-orders/{po_id}/order")
    r = c.post(f"/api/purchase-orders/{po_id}/receive", json={})
    expect(r.status_code == 200, f"stock in via PO ({r.status_code})")

    r = c.post("/api/sales", json={"lines": [{"product_id": p["id"], "quantity": 7}]})
    expect(r.status_code == 201, f"sale created ({r.text[:150]})")
    sale = r.json()
    expect(str(sale["total_revenue"]) in ("8.40", "8.4000"), f"revenue 7*1.20 = {sale['total_revenue']}")
    expect(str(sale["lines"][0]["unit_price"]) in ("1.2", "1.20"), "unit price defaults from product")

    on_hand = Decimal(c.get(f"/api/products/{p['id']}").json()["on_hand"])
    expect(on_hand == Decimal("93.00"), f"on_hand 100-7=93, got {on_hand}")

    r = c.post("/api/sales", json={"lines": [{"product_id": p["id"], "quantity": 500}]})
    expect(r.status_code == 400 and "Insufficient stock" in r.json()["detail"], "overselling rejected")

    r = c.get(f"/api/analytics/velocity/{p['id']}")
    daily_before = Decimal(r.json()["avg_daily_sales"])
    expect(daily_before > 0, f"velocity computed: {daily_before}")

backdate_last_sale("erp.db")

with TestClient(app) as c:
    login(c)
    p = c.get("/api/products", params={"q": "SODA"}).json()[0]
    pid = p["id"]

    v = c.get(f"/api/analytics/velocity/{pid}").json()
    daily = Decimal(v["avg_daily_sales"])
    expected_daily = (Decimal(7) / Decimal(30)).quantize(Decimal("0.0001"))
    got = daily.quantize(Decimal("0.0001"))
    expect(got == expected_daily,
           f"daily sales over fixed 30d window: {got} vs {expected_daily}")

    restock = {row["sku"]: row for row in c.get("/api/analytics/restock").json()}
    row = restock["SODA-1L"]
    rp = Decimal(row["reorder_point"])
    daily30 = Decimal(7) / Decimal(30)
    expected_rp = (Decimal(5) * daily30 + Decimal(10)).quantize(Decimal("0.01"))
    expect(rp == expected_rp, f"reorder_point = lead*daily+safety = {rp} vs {expected_rp}")

    suggested = Decimal(row["suggested_order_qty"])
    target = Decimal(12) * daily30 + Decimal(10)
    expected_suggested = max(target - on_hand, Decimal(0)).quantize(Decimal("0"))
    expect(suggested == expected_suggested, f"suggested qty = {suggested} vs {expected_suggested}")
    expect(row["status"] in ("ok", "low"), f"status sensible: {row['status']}")

    trend = c.get("/api/analytics/sales-trend", params={"product_id": pid}).json()
    expect(len(trend) >= 1 and Decimal(trend[0]["qty_sold"]) == Decimal("7.00"),
           f"trend has backdated bucket: {trend}")

    ov = c.get("/api/analytics/overview").json()
    expect(ov["active_products"] >= 1, f"overview KPIs: {ov['active_products']} SKUs, "
                                        f"stock value {ov['stock_value']}, rev30d {ov['revenue_30d']}")
    expect(Decimal(ov["revenue_30d"]) == Decimal("8.40"), f"revenue_30d = {ov['revenue_30d']}")

print("\nAll M3 backend smoke checks passed.")
