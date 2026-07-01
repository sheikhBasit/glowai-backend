from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import BeautyProfile, User
from services.claude import get_recommendations

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
@limiter.limit("20/minute")
async def recommendations(
    request: Request,
    occasion: str = "Everyday",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(BeautyProfile).filter(BeautyProfile.user_id == user.id).first()
    profile_data = {}
    if profile:
        profile_data = {
            "skin_tone": profile.skin_tone,
            "undertone": profile.undertone,
            "skin_type": profile.skin_type,
            "concerns": profile.concerns,
        }
    palettes = get_recommendations(profile_data, occasion)
    return {"occasion": occasion, "palettes": palettes}
