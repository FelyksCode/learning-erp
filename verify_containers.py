import json
import urllib.error
import urllib.request
from datetime import date

BASE = "http://localhost:8000/api"
RUN = date.today().isoformat().replace("-", "")


def call(path, method="GET", payload=None, token=None, form=None):
    data = None
    headers = {}
    if form is not None:
        data = form.encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"{method} {path} -> HTTP {e.code}: {body[:200]}")


token = call("/auth/token", "POST", form="username=admin&password=admin")[1]["access_token"]
print("1. login on Postgres-backed backend: OK")

sku = f"DOCKER-{RUN}"
status, cat = call("/catalog/categories", "POST", {"name": f"Containers {RUN}"}, token=token)
if status == 409:
    cats = call("/catalog/categories", token=token)[1]
    cat = next(c for c in cats if c["name"] == f"Containers {RUN}")

status, product = call(
    "/products",
    "POST",
    {"sku": sku, "name": "Container probe", "unit_cost": "2.00", "sale_price": "5.00",
     "category_id": cat["id"], "reorder_enabled": True, "lead_time_days": 4, "safety_stock": 5},
    token=token,
)
if status == 409:
    product = next(p for p in call("/products", token=token)[1] if p["sku"] == sku)
print(f"2. product ready: {product['sku']} (id {product['id']})")

call("/stock-moves", "POST",
     {"product_id": product["id"], "to_location_code": "SHOP",
      "quantity": 25, "unit_cost": "2.00", "reference": f"PO-DOCKER-{RUN}"}, token=token)
call("/sales", "POST", {"lines": [{"product_id": product["id"], "quantity": 6}]}, token=token)

on_hand = call(f"/products/{product['id']}", token=token)[1]["on_hand"]
assert float(on_hand) == 19.0, on_hand
print("3. ledger math across Postgres: receive 25 - sell 6 =", on_hand)

row = next(r for r in call("/analytics/restock", token=token)[1] if r["sku"] == sku)
assert row["status"] in ("low", "ok"), row
print("4. restock analytics:", row["status"], "| reorder point", row["reorder_point"],
      "| suggested qty", row["suggested_order_qty"])

audit = call("/audit", token=token)[1]
assert audit["total"] >= 3, audit["total"]
print("5. audit trail rows:", audit["total"])

with urllib.request.urlopen("http://localhost:3000/login") as res:
    assert res.status == 200 and b"Stock Ledger" in res.read()
print("6. frontend serving on :3000: OK")
