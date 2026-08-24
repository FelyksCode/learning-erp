from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.services.ai_service import AIError, generate_insight

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/insights")
def insights(db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.ai_enabled:
        return {
            "enabled": False,
            "reason": "AI is disabled. Set AI_ENABLED=true plus AI_API_KEY (OpenAI-compatible) in backend/.env.",
        }
    try:
        text = generate_insight(db)
    except AIError as exc:
        raise HTTPException(502, str(exc))
    return {"enabled": True, "insight": text}
