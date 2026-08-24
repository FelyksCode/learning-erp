import json

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def audit(
    db: Session,
    user: User | None,
    action: str,
    entity: str,
    entity_id: int | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "system",
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=json.dumps(detail, default=str) if detail else None,
        )
    )
    db.commit()
