from datetime import timedelta
from decimal import Decimal

import pytest

from app.models import Location, Product, Sale, SaleLine, StockMove
from app.models.base import utcnow
from app.services.inventory_service import (
    create_move,
    get_location_by_code,
    on_hand_for_product,
    validate_move_locations,
)
from app.services.sales_service import avg_daily_sales, restock_report

pytestmark = pytest.mark.unit


def _product(db, sku="T-1", **kwargs):
    product = Product(sku=sku, name=sku, **kwargs)
    db.add(product)
    db.commit()
    return product


def _move(db, product, qty, from_code=None, to_code=None):
    src = get_location_by_code(db, from_code) if from_code else None
    dst = get_location_by_code(db, to_code) if to_code else None
    return create_move(
        db,
        product_id=product.id,
        quantity=Decimal(qty),
        from_location_id=src.id if src else None,
        to_location_id=dst.id if dst else None,
    )


def test_on_hand_starts_at_zero(db_session):
    product = _product(db_session)

    assert on_hand_for_product(db_session, product.id) == Decimal("0")


def test_receive_sell_and_loss_change_on_hand(db_session):
    product = _product(db_session)
    _move(db_session, product, 100, from_code="SUPPLIER", to_code="SHOP")
    _move(db_session, product, 35, from_code="SHOP", to_code="CUSTOMER")
    _move(db_session, product, 2, from_code="SHOP", to_code="LOSS")

    assert on_hand_for_product(db_session, product.id) == Decimal("63.00")


def test_internal_transfer_is_on_hand_neutral(db_session):
    product = _product(db_session)
    _move(db_session, product, 50, from_code="SUPPLIER", to_code="SHOP")
    before = on_hand_for_product(db_session, product.id)

    _move(db_session, product, 10, from_code="SHOP", to_code="STORAGE")

    assert on_hand_for_product(db_session, product.id) == before


def test_invalid_direction_is_rejected_before_touching_the_ledger(db_session):
    with pytest.raises(ValueError, match="Invalid move direction"):
        validate_move_locations(db_session, "SUPPLIER", "LOSS")


def test_omitted_side_defaults_to_supplier_or_customer(db_session):
    src, dst = validate_move_locations(db_session, None, "SHOP")

    assert src.code == "SUPPLIER"
    assert dst.code == "SHOP"

    src, dst = validate_move_locations(db_session, "SHOP", None)

    assert src.code == "SHOP"
    assert dst.code == "CUSTOMER"


def _sell(db, product, qty, days_ago):
    sold_at = utcnow() - timedelta(days=days_ago)
    sale = Sale(sold_at=sold_at, reference=f"TEST-{days_ago}-{qty}")
    db.add(sale)
    db.flush()
    db.add(SaleLine(sale_id=sale.id, product_id=product.id, quantity=Decimal(qty), unit_price="1.00"))
    db.commit()


def test_velocity_divides_by_full_window_not_days_since_sale(db_session):
    product = _product(db_session)
    _sell(db_session, product, 7, days_ago=10)

    daily = avg_daily_sales(db_session, product.id)

    assert daily == Decimal("7") / Decimal("30")


def test_no_sales_means_zero_velocity(db_session):
    product = _product(db_session)

    assert avg_daily_sales(db_session, product.id) == Decimal("0")


def test_reorder_point_and_suggested_qty_follow_formula(db_session):
    product = _product(
        db_session,
        sku="RP-1",
        reorder_enabled=True,
        lead_time_days=5,
        safety_stock=Decimal("10"),
    )
    _sell(db_session, product, 7, days_ago=5)

    rows = {row["sku"]: row for row in restock_report(db_session)}
    row = rows["RP-1"]
    daily = Decimal(7) / Decimal(30)

    assert row["reorder_point"] == (Decimal(5) * daily + Decimal(10)).quantize(Decimal("0.01"))
    assert row["suggested_order_qty"] == ((Decimal(12) * daily + Decimal(10)) - Decimal("0")).quantize(
        Decimal("0")
    )


def test_restock_status_ladder(db_session):
    tracked = _product(db_session, sku="ST-LOW", reorder_enabled=True, lead_time_days=1, safety_stock=Decimal("500"))
    untracked = _product(db_session, sku="ST-OFF")

    rows = {row["sku"]: row for row in restock_report(db_session)}

    assert rows["ST-LOW"]["status"] == "low"
    assert rows["ST-OFF"]["status"] == "not-tracked"
