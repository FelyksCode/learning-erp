from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import LocationType, StockMove, User
from app.schemas.inventory import StockMoveIn
from app.services.audit_service import audit
from app.services.inventory_service import create_move, validate_move_locations

router = APIRouter(prefix="/stock-moves", tags=["stock"])


class MoveOut(BaseModel):
    id: int
    product_id: int
    from_location_id: int | None
    to_location_id: int | None
    quantity: Decimal
    unit_cost: Decimal | None
    reference: str | None
    moved_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[MoveOut])
def list_moves(
    product_id: int | None = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(StockMove).order_by(StockMove.moved_at.desc()).limit(limit)
    if product_id is not None:
        stmt = stmt.where(StockMove.product_id == product_id)
    return db.scalars(stmt).all()


@router.post("", response_model=MoveOut, status_code=201)
def post_move(
    payload: StockMoveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        src, dst = validate_move_locations(db, payload.from_location_code, payload.to_location_code)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if src.location_type == LocationType.SUPPLIER and payload.unit_cost is None:
        raise HTTPException(400, "unit_cost is required when receiving stock from a supplier")

    move = create_move(
        db,
        product_id=payload.product_id,
        quantity=payload.quantity,
        from_location_id=src.id,
        to_location_id=dst.id,
        unit_cost=payload.unit_cost,
        reference=payload.reference,
    )
    audit(
        db,
        current_user,
        "stock-move",
        "product",
        move.product_id,
        {
            "move_id": move.id,
            "from": src.code,
            "to": dst.code,
            "quantity": str(move.quantity),
            "reference": move.reference,
        },
    )
    return move
