from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

Money = Annotated[Decimal, Field(max_digits=13, decimal_places=2)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class SaleLineIn(BaseModel):
    product_id: int
    quantity: Quantity
    unit_price: Money | None = None


class SaleCreate(BaseModel):
    customer_id: int | None = None
    reference: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=500)
    lines: list[SaleLineIn] = Field(min_length=1)


class SaleLineOut(BaseModel):
    id: int
    product_id: int
    product_sku: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal

    @classmethod
    def from_line(cls, line) -> "SaleLineOut":
        return cls(
            id=line.id,
            product_id=line.product_id,
            product_sku=line.product.sku,
            product_name=line.product.name,
            quantity=line.quantity,
            unit_price=line.unit_price,
        )


class SaleOut(BaseModel):
    id: int
    reference: str | None
    customer_id: int | None
    sold_at: object
    total_revenue: Decimal
    lines: list[SaleLineOut]


class OverviewOut(BaseModel):
    active_products: int
    stock_value: Decimal
    low_stock_count: int
    out_of_stock_count: int
    revenue_today: Decimal
    revenue_7d: Decimal
    revenue_30d: Decimal


class RestockRow(BaseModel):
    product_id: int
    sku: str
    name: str
    on_hand: Decimal
    avg_daily_sales: Decimal
    days_of_cover: Decimal | None
    reorder_point: Decimal
    suggested_order_qty: Decimal
    status: str


class TrendPoint(BaseModel):
    date: str
    qty_sold: Decimal
    revenue: Decimal
