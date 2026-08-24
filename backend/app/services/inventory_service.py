from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Location, LocationType, StockMove

ALLOWED_TRANSITIONS = {
    (LocationType.INTERNAL, LocationType.INTERNAL),
    (LocationType.INTERNAL, LocationType.CUSTOMER),
    (LocationType.INTERNAL, LocationType.LOSS),
    (LocationType.SUPPLIER, LocationType.INTERNAL),
    (LocationType.CUSTOMER, LocationType.INTERNAL),
    (LocationType.LOSS, LocationType.INTERNAL),
}


def get_location_by_code(db: Session, code: str) -> Location | None:
    return db.scalar(select(Location).where(Location.code == code))


def on_hand_for_product(db: Session, product_id: int) -> Decimal:
    to_internal = (
        select(func.coalesce(func.sum(StockMove.quantity), 0))
        .join(Location, StockMove.to_location_id == Location.id)
        .where(StockMove.product_id == product_id)
        .where(Location.location_type == LocationType.INTERNAL)
    )
    from_internal = (
        select(func.coalesce(func.sum(StockMove.quantity), 0))
        .join(Location, StockMove.from_location_id == Location.id)
        .where(StockMove.product_id == product_id)
        .where(Location.location_type == LocationType.INTERNAL)
    )
    qty_in = Decimal(db.execute(to_internal).scalar_one())
    qty_out = Decimal(db.execute(from_internal).scalar_one())
    return qty_in - qty_out


def validate_move_locations(
    db: Session,
    from_code: str | None,
    to_code: str | None,
) -> tuple[Location, Location]:
    if not from_code and not to_code:
        raise ValueError("At least one of from_location_code or to_location_code is required")

    if from_code:
        src = get_location_by_code(db, from_code)
        if src is None:
            raise ValueError(f"Unknown location code: {from_code}")
    else:
        src = get_location_by_code(db, "SUPPLIER")
        if src is None:
            raise ValueError("Default SUPPLIER location missing; seed locations first")

    if to_code:
        dst = get_location_by_code(db, to_code)
        if dst is None:
            raise ValueError(f"Unknown location code: {to_code}")
    else:
        dst = get_location_by_code(db, "CUSTOMER")
        if dst is None:
            raise ValueError("Default CUSTOMER location missing; seed locations first")

    pair = (src.location_type, dst.location_type)
    if pair not in ALLOWED_TRANSITIONS:
        raise ValueError(f"Invalid move direction: {src.code} ({src.location_type}) -> {dst.code} ({dst.location_type})")

    return src, dst


def create_move(
    db: Session,
    *,
    product_id: int,
    quantity: Decimal,
    from_location_id: int | None,
    to_location_id: int | None,
    unit_cost: Decimal | None = None,
    reference: str | None = None,
) -> StockMove:
    move = StockMove(
        product_id=product_id,
        quantity=quantity,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        unit_cost=unit_cost,
        reference=reference,
    )
    db.add(move)
    db.commit()
    db.refresh(move)
    return move
