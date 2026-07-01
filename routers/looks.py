import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import Look, User
from schemas import LookCreate, LookOut
from services import storage

router = APIRouter(prefix="/looks", tags=["looks"])


@router.get("", response_model=list[LookOut])
def list_looks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    looks = (
        db.query(Look)
        .filter(Look.user_id == user.id)
        .order_by(Look.created_at.desc())
        .all()
    )
    return [LookOut.model_validate(l) for l in looks]


@router.post("", response_model=LookOut, status_code=status.HTTP_201_CREATED)
def create_look(
    body: LookCreate,
    thumbnail_b64: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    thumbnail_path = None
    if thumbnail_b64:
        try:
            img_bytes = base64.b64decode(thumbnail_b64)
            thumbnail_path = storage.save(img_bytes, "thumbnails", "jpg")
        except Exception:
            raise HTTPException(400, "Invalid thumbnail base64")

    look = Look(
        user_id=user.id,
        name=body.name,
        palette=body.palette,
        zones=body.zones,
        occasion=body.occasion,
        thumbnail_path=thumbnail_path,
        score=body.score,
    )
    db.add(look)
    db.commit()
    db.refresh(look)
    return LookOut.model_validate(look)


@router.get("/{look_id}", response_model=LookOut)
def get_look(look_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    look = db.get(Look, look_id)
    if not look or look.user_id != user.id:
        raise HTTPException(404, "Look not found")
    return LookOut.model_validate(look)


@router.patch("/{look_id}/score", response_model=LookOut)
def save_score(
    look_id: uuid.UUID,
    score: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    look = db.get(Look, look_id)
    if not look or look.user_id != user.id:
        raise HTTPException(404, "Look not found")
    look.score = score
    db.commit()
    db.refresh(look)
    return LookOut.model_validate(look)


@router.delete("/{look_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_look(look_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    look = db.get(Look, look_id)
    if not look or look.user_id != user.id:
        raise HTTPException(404, "Look not found")
    if look.thumbnail_path:
        storage.delete(look.thumbnail_path)
    db.delete(look)
    db.commit()
