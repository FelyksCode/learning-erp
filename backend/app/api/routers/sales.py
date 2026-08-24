from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Sale, SaleLine, User
from app.schemas.sales import OverviewOut, RestockRow, SaleCreate, SaleLineOut, SaleOut, TrendPoint
from app.services.audit_service import audit
from app.services.sales_service import (
    SalesError,
    avg_daily_sales,
    create_sale,
    overview,
    restock_report,
    sales_trend,
)

router = APIRouter(prefix="/sales", tags=["sales"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


def _to_out(sale: Sale) -> SaleOut:
    total = sum((line.quantity * line.unit_price for line in sale.lines), Decimal("0"))
    return SaleOut(
        id=sale.id,
        reference=sale.reference,
        customer_id=sale.customer_id,
        sold_at=sale.sold_at,
        total_revenue=total,
        lines=[SaleLineOut.from_line(line) for line in sale.lines],
    )


@router.get("", response_model=list[SaleOut])
def list_sales(
    product_id: int | None = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(Sale).order_by(Sale.sold_at.desc())
    if product_id is not None:
        stmt = stmt.join(SaleLine, SaleLine.sale_id == Sale.id).where(SaleLine.product_id == product_id)
    sales = db.scalars(stmt.limit(limit)).unique().all()
    return [_to_out(s) for s in sales]


@router.post("", response_model=SaleOut, status_code=201)
def create(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        sale = create_sale(db, payload)
    except SalesError as exc:
        raise HTTPException(400, str(exc))
    audit(db, current_user, "create", "sale", sale.id,
          {"lines": len(sale.lines), "reference": sale.reference})
    return _to_out(sale)


class VelocityOut(BaseModel):
    product_id: int
    window_days: int
    avg_daily_sales: Decimal


@analytics_router.get("/overview", response_model=OverviewOut)
def get_overview(db: Session = Depends(get_db)):
    return overview(db)


@analytics_router.get("/restock", response_model=list[RestockRow])
def get_restock(window_days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    return restock_report(db, window_days)


@analytics_router.get("/sales-trend", response_model=list[TrendPoint])
def get_trend(
    days: int = Query(default=30, ge=1, le=365),
    product_id: int | None = None,
    db: Session = Depends(get_db),
):
    return sales_trend(db, days, product_id)


@analytics_router.get("/velocity/{product_id}", response_model=VelocityOut)
def get_velocity(
    product_id: int,
    window_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return VelocityOut(
        product_id=product_id,
        window_days=window_days,
        avg_daily_sales=avg_daily_sales(db, product_id, window_days).quantize(Decimal("0.0001")),
    )
