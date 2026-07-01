from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import Look, User
from schemas import ScoreRequest, ScoreResponse
from services.claude import score_look

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/score", tags=["score"])


@router.post("", response_model=ScoreResponse)
@limiter.limit("20/minute")
async def score(
    request: Request,
    body: ScoreRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = score_look(body.photo_base64, body.occasion, body.makeup)
    return ScoreResponse(**result)
