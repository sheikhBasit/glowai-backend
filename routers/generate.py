import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from deps import get_current_user
from models import User
from plan_limits import is_pro
from schemas import AiLookRequest, AiLookResponse
from services.claude import analyze_and_generate

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/ai-look", response_model=AiLookResponse)
@limiter.limit("5/minute")
async def generate_ai_look(
    request: Request,
    body: AiLookRequest,
    user: User = Depends(get_current_user),
):
    if not is_pro(user):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "AI look generation is a Pro feature — upgrade to unlock it")
    return await analyze_and_generate(body.arB64, body.activeZones, body.colors, body.occasion, body.skinTone, body.undertone)
