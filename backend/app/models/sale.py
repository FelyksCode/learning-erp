from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Sale(Base, TimestampMixin):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    lines: Mapped[list["SaleLine"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="joined",
        order_by="SaleLine.id",
    )


class SaleLine(Base):
    __tablename__ = "sale_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(13, 2))

    sale: Mapped["Sale"] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship(lazy="joined")
