from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

Money = Annotated[Decimal, Field(max_digits=13, decimal_places=2)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: int | None = None


class CategoryOut(BaseModel):
    id: int
    name: str
    parent_id: int | None

    model_config = {"from_attributes": True}


class PartnerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    partner_type: str = Field(pattern="^(supplier|customer)$")
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class PartnerOut(BaseModel):
    id: int
    name: str
    partner_type: str
    phone: str | None
    email: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    category_id: int | None = None
    unit_cost: Money = Decimal("0")
    sale_price: Money = Decimal("0")
    reorder_enabled: bool = False
    lead_time_days: int = Field(default=7, ge=0)
    safety_stock: Quantity = Decimal("0")


class ProductUpdate(BaseModel):
    barcode: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: int | None = None
    unit_cost: Money | None = None
    sale_price: Money | None = None
    reorder_enabled: bool | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    safety_stock: Quantity | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    id: int
    sku: str
    barcode: str | None
    name: str
    category_id: int | None
    unit_cost: Decimal
    sale_price: Decimal
    reorder_enabled: bool
    lead_time_days: int
    safety_stock: Decimal
    is_active: bool

    model_config = {"from_attributes": True}


class ProductWithStockOut(ProductOut):
    on_hand: Decimal


class StockMoveIn(BaseModel):
    product_id: int
    from_location_code: str | None = None
    to_location_code: str | None = None
    quantity: Quantity
    unit_cost: Money | None = None
    reference: str | None = None


class StockMoveOut(BaseModel):
    id: int
    product_id: int
    from_location_id: int | None
    to_location_id: int | None
    quantity: Decimal
    unit_cost: Decimal | None
    reference: str | None
    moved_at: object

    model_config = {"from_attributes": True}
