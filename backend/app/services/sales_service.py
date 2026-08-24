from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Location,
    LocationType,
    Partner,
    PartnerType,
    Product,
    Sale,
    SaleLine,
    StockMove,
)
from app.models.base import utcnow
from app.services.inventory_service import create_move, on_hand_for_product

DEFAULT_WINDOW_DAYS = 30
REVIEW_PERIOD_DAYS = 7


class SalesError(Exception):
    pass


def _customer_location(db: Session):
    loc = db.scalar(select(Location).where(Location.code == "CUSTOMER"))
    if loc is None:
        raise SalesError("Default CUSTOMER location missing; seed locations first")
    return loc


def _shop_locations(db: Session) -> list[int]:
    return list(
        db.scalars(
            select(Location.id).where(Location.location_type == LocationType.INTERNAL)
        )
    )


def create_sale(db: Session, payload) -> Sale:
    customer = None
    if payload.customer_id is not None:
        customer = db.get(Partner, payload.customer_id)
        if not customer or customer.partner_type != PartnerType.CUSTOMER:
            raise SalesError(f"Customer {payload.customer_id} not found or is not a customer")

    product_ids = {line.product_id for line in payload.lines}
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids)))}
    missing = product_ids - products.keys()
    if missing:
        raise SalesError(f"Unknown products: {sorted(missing)}")

    sale = Sale(
        reference=payload.reference,
        customer_id=customer.id if customer else None,
        notes=payload.notes,
        sold_at=utcnow(),
        lines=[
            SaleLine(
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price=(
                    line.unit_price
                    if line.unit_price is not None
                    else products[line.product_id].sale_price
                ),
            )
            for line in payload.lines
        ],
    )
    db.add(sale)
    db.flush()

    dest = _customer_location(db)
    internal_ids = set(_shop_locations(db))
    for line in sale.lines:
        available = on_hand_for_product(db, line.product_id)
        if available < line.quantity:
            db.rollback()
            raise SalesError(
                f"Insufficient stock for {products[line.product_id].sku}: "
                f"on hand {available}, requested {line.quantity}"
            )
        source = db.scalar(
            select(StockMove.to_location_id)
            .join(Location, StockMove.to_location_id == Location.id)
            .where(
                StockMove.product_id == line.product_id,
                Location.location_type == LocationType.INTERNAL,
            )
            .group_by(StockMove.to_location_id)
            .order_by(func.sum(StockMove.quantity).desc())
            .limit(1)
        )
        src_id = source if source in internal_ids else min(internal_ids)
        create_move(
            db,
            product_id=line.product_id,
            quantity=line.quantity,
            from_location_id=src_id,
            to_location_id=dest.id,
            unit_cost=None,
            reference=f"SALE-{sale.id}" + (f"/{sale.reference}" if sale.reference else ""),
        )

    db.commit()
    db.refresh(sale)
    return sale


def avg_daily_sales(db: Session, product_id: int, window_days: int = DEFAULT_WINDOW_DAYS) -> Decimal:
    cutoff = utcnow() - timedelta(days=window_days)
    qty = db.scalar(
        select(func.coalesce(func.sum(SaleLine.quantity), 0))
        .join(Sale, SaleLine.sale_id == Sale.id)
        .where(
            SaleLine.product_id == product_id,
            Sale.sold_at >= cutoff,
        )
    )
    return Decimal(qty) / Decimal(window_days)


def restock_report(db: Session, window_days: int = DEFAULT_WINDOW_DAYS) -> list[dict]:
    products = db.scalars(select(Product).where(Product.is_active.is_(True))).all()
    rows = []
    for p in products:
        on_hand = on_hand_for_product(db, p.id)
        daily = avg_daily_sales(db, p.id, window_days)
        reorder_point = (
            Decimal(p.lead_time_days) * daily + p.safety_stock if p.reorder_enabled else Decimal("0")
        )
        target_qty = (Decimal(p.lead_time_days + REVIEW_PERIOD_DAYS)) * daily + p.safety_stock
        suggested = max(target_qty - on_hand, Decimal("0")) if p.reorder_enabled else Decimal("0")

        cover = None
        if daily > 0:
            cover = on_hand / daily

        if not p.reorder_enabled:
            status = "not-tracked"
        elif on_hand <= 0 and daily > 0:
            status = "out-of-stock"
        elif on_hand <= reorder_point:
            status = "low"
        elif daily == 0:
            status = "no-sales"
        else:
            status = "ok"

        rows.append(
            {
                "product_id": p.id,
                "sku": p.sku,
                "name": p.name,
                "on_hand": on_hand,
                "avg_daily_sales": daily.quantize(Decimal("0.01")),
                "days_of_cover": None if cover is None else cover.quantize(Decimal("0.1")),
                "reorder_point": reorder_point.quantize(Decimal("0.01")),
                "suggested_order_qty": suggested.quantize(Decimal("0")),
                "status": status,
            }
        )

    priority = {"out-of-stock": 0, "low": 1, "no-sales": 2, "ok": 3, "not-tracked": 4}
    rows.sort(key=lambda r: (priority[r["status"]], -r["avg_daily_sales"]))
    return rows


def overview(db: Session) -> dict:
    now = utcnow()
    active_products = db.scalar(
        select(func.count()).select_from(Product).where(Product.is_active.is_(True))
    )
    costs_by_product = dict(db.execute(select(Product.id, Product.unit_cost)).all())
    low = out = 0
    stock_value = Decimal("0")
    for row in restock_report(db):
        unit_cost = costs_by_product.get(row["product_id"], Decimal("0"))
        stock_value += row["on_hand"] * unit_cost
        if row["status"] in ("low", "out-of-stock"):
            low += 1
        if row["status"] == "out-of-stock":
            out += 1

    def revenue_since(days: int) -> Decimal:
        cutoff = now - timedelta(days=days)
        total = db.scalar(
            select(func.coalesce(func.sum(SaleLine.quantity * SaleLine.unit_price), 0)).join(
                Sale, SaleLine.sale_id == Sale.id
            ).where(Sale.sold_at >= cutoff)
        )
        return Decimal(total)

    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_total = db.scalar(
        select(func.coalesce(func.sum(SaleLine.quantity * SaleLine.unit_price), 0)).join(
            Sale, SaleLine.sale_id == Sale.id
        ).where(Sale.sold_at >= midnight)
    )
    return {
        "active_products": int(active_products),
        "stock_value": stock_value.quantize(Decimal("0.01")),
        "low_stock_count": low,
        "out_of_stock_count": out,
        "revenue_today": Decimal(today_total).quantize(Decimal("0.01")),
        "revenue_7d": revenue_since(7),
        "revenue_30d": revenue_since(30),
    }


def sales_trend(db: Session, days: int = 30, product_id: int | None = None) -> list[dict]:
    cutoff = utcnow() - timedelta(days=days)
    day = func.date(Sale.sold_at).label("day")
    stmt = (
        select(
            day,
            func.coalesce(func.sum(SaleLine.quantity), 0).label("qty"),
            func.coalesce(func.sum(SaleLine.quantity * SaleLine.unit_price), 0).label("rev"),
        )
        .join(Sale, SaleLine.sale_id == Sale.id)
        .where(Sale.sold_at >= cutoff)
        .group_by(day)
        .order_by(day)
    )
    if product_id is not None:
        stmt = stmt.where(SaleLine.product_id == product_id)
    result = db.execute(stmt).all()
    return [
        {
            "date": str(row.day),
            "qty_sold": Decimal(row.qty),
            "revenue": Decimal(row.rev).quantize(Decimal("0.01")),
        }
        for row in result
    ]
