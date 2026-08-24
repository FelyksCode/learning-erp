from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import Category, Partner, PartnerType, Product, User
from app.schemas.inventory import (
    CategoryIn,
    CategoryOut,
    PartnerIn,
    PartnerOut,
    ProductIn,
    ProductOut,
    ProductUpdate,
    ProductWithStockOut,
)
from app.services.audit_service import audit
from app.services.inventory_service import on_hand_for_product

router = APIRouter(prefix="/products", tags=["products"])
misc_router = APIRouter(prefix="/catalog", tags=["catalog"])


@misc_router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.name)).all()


@misc_router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(payload: CategoryIn, db: Session = Depends(get_db)):
    cat = Category(**payload.model_dump())
    db.add(cat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Category name already exists")
    db.refresh(cat)
    return cat


@misc_router.get("/partners", response_model=list[PartnerOut])
def list_partners(
    partner_type: str | None = Query(default=None, pattern="^(supplier|customer)$"),
    db: Session = Depends(get_db),
):
    stmt = select(Partner).order_by(Partner.name)
    if partner_type:
        stmt = stmt.where(Partner.partner_type == PartnerType(partner_type))
    return db.scalars(stmt).all()


@misc_router.post("/partners", response_model=PartnerOut, status_code=201)
def create_partner(payload: PartnerIn, db: Session = Depends(get_db)):
    partner = Partner(name=payload.name, partner_type=PartnerType(payload.partner_type))
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


@router.get("", response_model=list[ProductWithStockOut])
def list_products(
    q: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    stmt = select(Product).order_by(Product.sku)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Product.name.ilike(like)) | (Product.sku.ilike(like)) | (Product.barcode.ilike(like))
        )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    products = db.scalars(stmt).all()
    return [
        ProductWithStockOut(**ProductOut.model_validate(p).model_dump(), on_hand=on_hand_for_product(db, p.id))
        for p in products
    ]


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "SKU or barcode already exists")
    db.refresh(product)
    audit(db, current_user, "create", "product", product.id, {"sku": product.sku})
    return product


@router.get("/{product_id}", response_model=ProductWithStockOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    base = ProductOut.model_validate(product).model_dump()
    return ProductWithStockOut(**base, on_hand=on_hand_for_product(db, product.id))


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    audit(db, current_user, "update", "product", product.id, data)
    return product


@router.delete("/{product_id}", status_code=204)
def deactivate_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    product.is_active = False
    db.commit()
    audit(db, current_user, "deactivate", "product", product.id, {"sku": product.sku})
