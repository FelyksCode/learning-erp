import json
from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.sales_service import overview, restock_report, sales_trend

SYSTEM_PROMPT = """You are a retail analyst helping the owner of a small shop decide what to restock.
You receive JSON with shop KPIs, a per-product restock report (on hand, avg daily sales, reorder point,
suggested order quantity, status) and a 14-day daily sales trend.

Write short actionable advice:
1. Start with items to order NOW (out-of-stock or low) — name SKU and quantity from suggested_order_qty.
2. Mention items selling fast even if still ok (watchlist).
3. Mention slow movers (no-sales) worth a promotion instead of restocking.
Rules: plain text bullets with "-", max ~150 words, no headings, never invent numbers not in the data."""


class AIError(Exception):
    pass


def build_context(db: Session) -> dict:
    return {
        "overview": overview(db),
        "restock": restock_report(db)[:15],
        "sales_trend_14d": sales_trend(db, days=14),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def generate_insight(db: Session) -> str:
    settings = get_settings()
    if not settings.ai_api_key:
        raise AIError("AI_API_KEY is not set")

    payload = {
        "model": settings.ai_model,
        "temperature": 0.2,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(build_context(db), default=str)},
        ],
    }
    try:
        resp = httpx.post(
            f"{settings.ai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.ai_api_key}"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise AIError(f"LLM request failed: {exc}") from exc

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise AIError(f"Unexpected LLM response shape: {data}") from exc
