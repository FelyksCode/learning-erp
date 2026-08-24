import random
from datetime import datetime, timedelta, timezone

from app.core.db import SessionLocal, engine
from app.models import (
    Category,
    Location,
    LocationType,
    Partner,
    PartnerType,
    Product,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    Sale,
    SaleLine,
    StockMove,
)
from app.models.base import Base, utcnow

random.seed(42)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

PRODUCTS = [
    ("COLA-330", "Cola 330ml", "Beverages", 0.40, 1.00, 300, 5, 24),
    ("WATER-500", "Water 500ml", "Beverages", 0.10, 0.35, 450, 3, 48),
    ("JUICE-1L", "Orange juice 1L", "Beverages", 0.90, 2.20, 130, 7, 12),
    ("CHIPS-50", "Chips 50g", "Snacks", 0.30, 0.90, 290, 4, 36),
    ("CHOC-90", "Chocolate bar 90g", "Snacks", 0.55, 1.40, 105, 6, 18),
    ("SOAP-100", "Soap 100g", "Household", 0.25, 0.75, 95, 10, 8),
    ("TISSUE-200", "Tissues 200 sheets", "Household", 0.45, 1.10, 44, 12, 6),
]

now = utcnow()

with SessionLocal() as db:
    locs = {
        "SUPPLIER": Location(code="SUPPLIER", name="Suppliers", location_type=LocationType.SUPPLIER),
        "SHOP": Location(code="SHOP", name="Shop floor", location_type=LocationType.INTERNAL),
        "STORAGE": Location(code="STORAGE", name="Back storage", location_type=LocationType.INTERNAL),
        "CUSTOMER": Location(code="CUSTOMER", name="Customers", location_type=LocationType.CUSTOMER),
        "LOSS": Location(code="LOSS", name="Loss / adjustments", location_type=LocationType.LOSS),
    }
    db.add_all(locs.values())

    cats = {}
    for _, _, cat_name, *_ in PRODUCTS:
        if cat_name not in cats:
            cats[cat_name] = Category(name=cat_name)
            db.add(cats[cat_name])

    supplier = Partner(name="Metro Wholesale", partner_type=PartnerType.SUPPLIER)
    db.add(supplier)
    db.flush()

    products = []
    po = PurchaseOrder(
        supplier_id=supplier.id,
        reference="INITIAL-STOCK",
        status=PurchaseOrderStatus.RECEIVED,
        ordered_at=now - timedelta(days=28),
        received_at=now - timedelta(days=27),
    )
    db.add(po)
    db.flush()

    for sku, name, cat, cost, price, qty, lead, safety in PRODUCTS:
        p = Product(
            sku=sku,
            name=name,
            category_id=cats[cat].id,
            unit_cost=str(cost),
            sale_price=str(price),
            reorder_enabled=True,
            lead_time_days=lead,
            safety_stock=safety,
        )
        db.add(p)
        products.append((p, qty))
        db.add(
            StockMove(
                product=p,
                quantity=str(qty),
                from_location_id=locs["SUPPLIER"].id,
                to_location_id=locs["SHOP"].id,
                unit_cost=str(cost),
                reference=f"PO-{po.id}/INITIAL-STOCK",
                moved_at=now - timedelta(days=27),
            )
        )
        db.add(
            PurchaseOrderLine(
                purchase_order_id=po.id,
                product=p,
                quantity=str(qty),
                quantity_received=str(qty),
                unit_cost=str(cost),
            )
        )
    db.commit()

    daily_base = {"COLA-330": 6, "WATER-500": 9, "JUICE-1L": 2, "CHIPS-50": 5, "CHOC-90": 3, "SOAP-100": 1.5, "TISSUE-200": 1}
    sold_totals = {p.sku: 0 for p, _ in products}

    for days_ago in range(26, -1, -1):
        day = now - timedelta(days=days_ago)
        weekday = day.weekday()
        weekend_boost = 1.6 if weekday >= 5 else 1.0
        growth = 1 + (26 - days_ago) * 0.01

        todays_sales = [
            (p, max(0, round(random.gauss(daily_base[p.sku], 1.5) * weekend_boost * growth)))
            for p, _ in products
        ]
        if all(q == 0 for _, q in todays_sales):
            continue

        sale = Sale(sold_at=day.replace(hour=random.randint(9, 19), minute=random.randint(0, 59)), reference=f"DAY-{days_ago}")
        db.add(sale)
        db.flush()
        for p, q in todays_sales:
            if q <= 0:
                continue
            sold_totals[p.sku] += q
            db.add(SaleLine(sale_id=sale.id, product_id=p.id, quantity=str(q), unit_price=p.sale_price))
            db.add(
                StockMove(
                    product_id=p.id,
                    quantity=str(q),
                    from_location_id=locs["SHOP"].id,
                    to_location_id=locs["CUSTOMER"].id,
                    reference=f"SALE-{sale.id}",
                    moved_at=sale.sold_at,
                )
            )

    for p, initial in products:
        remaining = initial - sold_totals[p.sku]
        print(f"{p.sku}: stocked {initial}, sold {sold_totals[p.sku]}, on hand {remaining}")

    db.commit()
    print("Demo data seeded.")
