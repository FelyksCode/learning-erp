from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    LocationType,
    Partner,
    PartnerType,
    Product,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
)
from app.models.base import utcnow
from app.schemas.purchasing import POCreate, ReceiveIn
from app.services.inventory_service import create_move, get_location_by_code


class PurchaseError(Exception):
    pass


def _get_po(db: Session, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if not po:
        raise PurchaseError(f"Purchase order {po_id} not found")
    return po


def create_po(db: Session, payload: POCreate) -> PurchaseOrder:
    supplier = db.get(Partner, payload.supplier_id)
    if not supplier or supplier.partner_type != PartnerType.SUPPLIER:
        raise PurchaseError(f"Supplier {payload.supplier_id} not found or is not a supplier")

    product_ids = {line.product_id for line in payload.lines}
    products = {
        p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids)))
    }
    missing = product_ids - products.keys()
    if missing:
        raise PurchaseError(f"Unknown products: {sorted(missing)}")

    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        reference=payload.reference,
        notes=payload.notes,
        lines=[
            PurchaseOrderLine(
                product_id=line.product_id,
                quantity=line.quantity,
                unit_cost=line.unit_cost if line.unit_cost is not None else products[line.product_id].unit_cost,
            )
            for line in payload.lines
        ],
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return po


def mark_ordered(db: Session, po_id: int) -> PurchaseOrder:
    po = _get_po(db, po_id)
    if po.status != PurchaseOrderStatus.DRAFT:
        raise PurchaseError(f"Cannot order a purchase order in status '{po.status}'")
    po.status = PurchaseOrderStatus.ORDERED
    po.ordered_at = utcnow()
    db.commit()
    db.refresh(po)
    return po


def cancel_po(db: Session, po_id: int) -> PurchaseOrder:
    po = _get_po(db, po_id)
    if po.status == PurchaseOrderStatus.CANCELLED:
        raise PurchaseError("Purchase order is already cancelled")
    received = any(line.quantity_received > 0 for line in po.lines)
    if received:
        raise PurchaseError("Cannot cancel a purchase order with received quantities")
    if po.status not in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.ORDERED):
        raise PurchaseError(f"Cannot cancel a purchase order in status '{po.status}'")
    po.status = PurchaseOrderStatus.CANCELLED
    db.commit()
    db.refresh(po)
    return po


def receive_po(db: Session, po_id: int, payload: ReceiveIn) -> PurchaseOrder:
    po = _get_po(db, po_id)
    if po.status != PurchaseOrderStatus.ORDERED:
        raise PurchaseError(f"Can only receive purchase orders in status 'ordered' (got '{po.status}')")

    location = get_location_by_code(db, payload.location_code)
    if location is None:
        raise PurchaseError(f"Unknown location code: {payload.location_code}")
    if location.location_type != LocationType.INTERNAL:
        raise PurchaseError(f"Receiving destination must be an internal location (got '{location.code}')")
    supplier_location = _supplier_location(db)

    lines_by_id = {line.id: line for line in po.lines}
    if payload.lines is None:
        targets = [(line, line.quantity - line.quantity_received) for line in po.lines]
    else:
        seen = set()
        targets = []
        for item in payload.lines:
            if item.line_id in seen:
                raise PurchaseError(f"Duplicate line id in receive request: {item.line_id}")
            seen.add(item.line_id)
            line = lines_by_id.get(item.line_id)
            if line is None:
                raise PurchaseError(f"Line {item.line_id} does not belong to purchase order {po_id}")
            targets.append((line, item.quantity))

    for line, qty in targets:
        remaining = line.quantity - line.quantity_received
        if qty > remaining:
            raise PurchaseError(
                f"Line {line.id}: cannot receive {qty}, only {remaining} remaining"
            )

    for line, qty in targets:
        if qty <= 0:
            continue
        create_move(
            db,
            product_id=line.product_id,
            quantity=Decimal(qty),
            from_location_id=supplier_location.id,
            to_location_id=location.id,
            unit_cost=line.unit_cost,
            reference=f"PO-{po.id}" + (f"/{po.reference}" if po.reference else ""),
        )
        line.quantity_received += Decimal(qty)

    if all(line.quantity_received >= line.quantity for line in po.lines):
        po.status = PurchaseOrderStatus.RECEIVED
        po.received_at = utcnow()

    db.commit()
    db.refresh(po)
    return po


def _supplier_location(db: Session):
    loc = get_location_by_code(db, "SUPPLIER")
    if loc is None:
        raise PurchaseError("Default SUPPLIER location missing; seed locations first")
    return loc


def total_cost(po: PurchaseOrder) -> Decimal:
    return sum((line.unit_cost * line.quantity for line in po.lines), Decimal("0"))
