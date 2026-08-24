from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.db import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    _admin: User = Depends(require_admin),
    entity: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    rows = db.scalars(stmt).all()
    total = db.scalar(select(func.count()).select_from(AuditLog))
    return {
        "total": int(total or 0),
        "items": [
            {
                "id": r.id,
                "username": r.username,
                "action": r.action,
                "entity": r.entity,
                "entity_id": r.entity_id,
                "detail": r.detail,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }
