import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Category, Product, SaleLine, User
from app.services.audit_service import audit
from app.services.inventory_service import on_hand_for_product
from app.services.sales_service import avg_daily_sales

router = APIRouter(tags=["data-io"])

PRODUCT_CSV_COLUMNS = ["sku", "name", "category", "unit_cost", "sale_price", "lead_time_days", "safety_stock"]
SALES_CSV_COLUMNS = ["sold_at", "sale_id", "reference", "sku", "quantity", "unit_price", "line_revenue"]


@router.get("/export/products.csv")
def export_products(db: Session = Depends(get_db)):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["sku", "name", "category_id", "unit_cost", "sale_price", "on_hand", "avg_daily_sales_30d"])
    products = db.scalars(select(Product).order_by(Product.sku)).all()
    for p in products:
        writer.writerow(
            [
                p.sku,
                p.name,
                p.category_id or "",
                f"{p.unit_cost:.2f}",
                f"{p.sale_price:.2f}",
                f"{on_hand_for_product(db, p.id):.2f}",
                f"{avg_daily_sales(db, p.id):.4f}",
            ]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )


@router.get("/export/sales.csv")
def export_sales(db: Session = Depends(get_db)):
    from app.models import Sale

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(SALES_CSV_COLUMNS)
    stmt = (
        select(
            Sale.sold_at,
            Sale.id,
            Sale.reference,
            Product.sku,
            SaleLine.quantity,
            SaleLine.unit_price,
        )
        .join_from(SaleLine, Sale, SaleLine.sale_id == Sale.id)
        .join_from(SaleLine, Product, SaleLine.product_id == Product.id)
        .order_by(Sale.sold_at, SaleLine.id)
    )
    for sold_at, sale_id, reference, sku, qty, price in db.execute(stmt):
        writer.writerow(
            [sold_at.isoformat(), sale_id, reference or "", sku, f"{qty:.2f}", f"{price:.2f}", f"{qty * price:.2f}"]
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales.csv"},
    )


@router.post("/import/products")
async def import_products(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")

    raw = await file.read()
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        required = {"sku", "name"}
        if reader.fieldnames is None or not required.issubset({(f or "").strip().lower() for f in reader.fieldnames}):
            raise HTTPException(400, f"CSV must contain columns: {', '.join(PRODUCT_CSV_COLUMNS)}")

        created = updated = skipped = 0
        for row in reader:
            row = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }
            sku = row.get("sku", "")
            name = row.get("name", "")
            if not sku or not name:
                skipped += 1
                continue

            category = None
            cat_name = row.get("category", "")
            if cat_name:
                category = db.scalar(select(Category).where(Category.name == cat_name))
                if category is None:
                    category = Category(name=cat_name)
                    db.add(category)
                    db.flush()

            values = {
                "name": name,
                "unit_cost": row.get("unit_cost") or None,
                "sale_price": row.get("sale_price") or None,
            }
            product = db.scalar(select(Product).where(Product.sku == sku))
            if product:
                product.name = name
                if values["unit_cost"]:
                    product.unit_cost = values["unit_cost"]
                if values["sale_price"]:
                    product.sale_price = values["sale_price"]
                if category:
                    product.category_id = category.id
                updated += 1
            else:
                db.add(
                    Product(
                        sku=sku,
                        name=name,
                        unit_cost=values["unit_cost"] or 0,
                        sale_price=values["sale_price"] or 0,
                        category_id=category.id if category else None,
                    )
                )
                created += 1
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - any malformed row must become a clean 400
        db.rollback()
        raise HTTPException(400, f"Import failed: {exc}")

    audit(db, current_user, "import", "product", None,
          {"file": file.filename, "created": created, "updated": updated, "skipped": skipped})
    return {"created": created, "updated": updated, "skipped": skipped}
