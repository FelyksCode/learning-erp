from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import PurchaseOrder, PurchaseOrderStatus, User
from app.schemas.purchasing import POCreate, POLineOut, POOut, ReceiveIn
from app.services.audit_service import audit
from app.services.purchasing_service import (
    PurchaseError,
    cancel_po,
    create_po,
    mark_ordered,
    receive_po,
    total_cost,
)

router = APIRouter(prefix="/purchase-orders", tags=["purchasing"])


def _to_out(po: PurchaseOrder) -> POOut:
    return POOut(
        id=po.id,
        supplier_id=po.supplier_id,
        status=po.status.value if isinstance(po.status, PurchaseOrderStatus) else po.status,
        reference=po.reference,
        notes=po.notes,
        ordered_at=po.ordered_at,
        received_at=po.received_at,
        total_cost=total_cost(po),
        lines=[POLineOut.from_line(line) for line in po.lines],
    )


def _translate(fn, *args):
    try:
        return fn(*args)
    except PurchaseError as exc:
        raise HTTPException(400, str(exc))


@router.get("", response_model=list[POOut])
def list_pos(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(PurchaseOrder).order_by(PurchaseOrder.id.desc())
    if status:
        try:
            stmt = stmt.where(PurchaseOrder.status == PurchaseOrderStatus(status))
        except ValueError:
            raise HTTPException(400, f"Unknown status: {status}")
    return [_to_out(po) for po in db.scalars(stmt).unique().all()]


@router.post("", response_model=POOut, status_code=201)
def create(payload: POCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = _translate(create_po, db, payload)
    audit(db, current_user, "create", "purchase-order", po.id,
          {"supplier_id": po.supplier_id, "lines": len(po.lines), "total": str(total_cost(po))})
    return _to_out(po)


@router.get("/{po_id}", response_model=POOut)
def get_one(po_id: int, db: Session = Depends(get_db)):
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(404, "Purchase order not found")
    return _to_out(po)


@router.post("/{po_id}/order", response_model=POOut)
def order(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = _translate(mark_ordered, db, po_id)
    audit(db, current_user, "order", "purchase-order", po.id, {"reference": po.reference})
    return _to_out(po)


@router.post("/{po_id}/receive", response_model=POOut)
def receive(
    po_id: int,
    payload: ReceiveIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requested = payload.lines
    po = _translate(receive_po, db, po_id, payload)
    audit(db, current_user, "receive", "purchase-order", po.id,
          {"location": payload.location_code,
           "lines": [item.model_dump() for item in requested] if requested else "all-remaining",
           "status": po.status.value if hasattr(po.status, "value") else str(po.status)})
    return _to_out(po)


@router.post("/{po_id}/cancel", response_model=POOut)
def cancel(po_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    po = _translate(cancel_po, db, po_id)
    audit(db, current_user, "cancel", "purchase-order", po.id, {"reference": po.reference})
    return _to_out(po)
