import enum

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LocationType(str, enum.Enum):
    INTERNAL = "internal"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    LOSS = "loss"


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("code", name="uq_locations_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    location_type: Mapped[LocationType] = mapped_column(
        Enum(LocationType, native_enum=False), default=LocationType.INTERNAL
    )
