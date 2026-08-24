from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.deps import get_current_user
from app.api.routers import ai, audit, auth, data_io, inventory, purchasing, sales, stock_moves
from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.security import hash_password
from app.models import Location, LocationType, User, UserRole
from app.models.base import Base

DEFAULT_LOCATIONS = [
    ("SUPPLIER", "Suppliers", LocationType.SUPPLIER),
    ("SHOP", "Shop floor", LocationType.INTERNAL),
    ("STORAGE", "Back storage", LocationType.INTERNAL),
    ("CUSTOMER", "Customers", LocationType.CUSTOMER),
    ("LOSS", "Loss / adjustments", LocationType.LOSS),
]

DEFAULT_ADMIN = ("admin", "admin", "Shop Owner")


def seed_locations(db) -> None:
    existing = set(db.scalars(select(Location.code)))
    for code, name, loc_type in DEFAULT_LOCATIONS:
        if code not in existing:
            db.add(Location(code=code, name=name, location_type=loc_type))


def seed_admin_user(db) -> None:
    has_users = db.scalar(select(User.id).limit(1)) is not None
    if not has_users:
        db.add(
            User(
                username=DEFAULT_ADMIN[0],
                password_hash=hash_password(DEFAULT_ADMIN[1]),
                full_name=DEFAULT_ADMIN[2],
                role=UserRole.ADMIN,
            )
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if get_settings().auto_create_tables:
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_locations(db)
        seed_admin_user(db)
        db.commit()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    protected = [Depends(get_current_user)]
    app.include_router(auth.router, prefix="/api")
    for router in (
        inventory.router,
        inventory.misc_router,
        stock_moves.router,
        purchasing.router,
        sales.router,
        sales.analytics_router,
        ai.router,
        data_io.router,
        audit.router,
    ):
        app.include_router(router, prefix="/api", dependencies=protected)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
