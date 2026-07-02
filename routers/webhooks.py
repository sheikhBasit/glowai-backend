import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from deps import get_db
from models import User

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

PRO_EVENT_TYPES = {"INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE", "UNCANCELLATION", "NON_RENEWING_PURCHASE"}
FREE_EVENT_TYPES = {"EXPIRATION", "CANCELLATION"}


@router.post("/revenuecat", status_code=status.HTTP_200_OK)
async def revenuecat_webhook(request: Request, db: Session = Depends(get_db)):
    secret = os.getenv("REVENUECAT_WEBHOOK_SECRET")
    if secret and request.headers.get("Authorization") != secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook secret")

    payload = await request.json()
    event = payload.get("event", {})
    event_type = event.get("type")
    app_user_id = event.get("app_user_id")

    try:
        user_id = uuid.UUID(app_user_id)
    except (TypeError, ValueError):
        return {"status": "ignored", "reason": "app_user_id is not a known user"}

    user = db.get(User, user_id)
    if not user:
        return {"status": "ignored", "reason": "user not found"}

    if event_type in PRO_EVENT_TYPES:
        user.plan = "pro"
        expiration_ms = event.get("expiration_at_ms")
        user.plan_expires_at = (
            datetime.fromtimestamp(expiration_ms / 1000, tz=timezone.utc) if expiration_ms else None
        )
        db.commit()
    elif event_type in FREE_EVENT_TYPES:
        user.plan = "free"
        user.plan_expires_at = None
        db.commit()

    return {"status": "ok"}
