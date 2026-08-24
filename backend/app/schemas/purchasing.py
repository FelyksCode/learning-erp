from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

Money = Annotated[Decimal, Field(max_digits=13, decimal_places=2)]
Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class POLineIn(BaseModel):
    product_id: int
    quantity: Quantity
    unit_cost: Money | None = None


class POCreate(BaseModel):
    supplier_id: int
    reference: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=500)
    lines: list[POLineIn] = Field(min_length=1)


class POLineOut(BaseModel):
    id: int
    product_id: int
    product_sku: str
    product_name: str
    quantity: Decimal
    quantity_received: Decimal
    unit_cost: Decimal

    model_config = {"from_attributes": True}

    @classmethod
    def from_line(cls, line) -> "POLineOut":
        return cls(
            id=line.id,
            product_id=line.product_id,
            product_sku=line.product.sku,
            product_name=line.product.name,
            quantity=line.quantity,
            quantity_received=line.quantity_received,
            unit_cost=line.unit_cost,
        )


class POOut(BaseModel):
    id: int
    supplier_id: int
    status: str
    reference: str | None
    notes: str | None
    ordered_at: object | None
    received_at: object | None
    total_cost: Decimal
    lines: list[POLineOut]


class ReceiveLineIn(BaseModel):
    line_id: int
    quantity: Quantity


class ReceiveIn(BaseModel):
    location_code: str = "SHOP"
    lines: list[ReceiveLineIn] | None = None
