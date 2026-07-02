import base64
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import DiaryEntry, User
from plan_limits import DIARY_LIMIT_FREE, is_pro
from schemas import DiaryOut, DiaryUpdate
from services import storage

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/diary", tags=["diary"])


class ProductUsed(BaseModel):
    item: str
    color: str


class DiaryCreate(BaseModel):
    title: str
    content: str | None = None
    occasion: str | None = None
    look_id: str | None = None
    image_base64: str | None = None
    score: float | None = None
    products_used: list[ProductUsed] | None = None
    tags: list[str] = []


@router.get("", response_model=list[DiaryOut])
def list_entries(
    page: int = 1,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    entries = (
        db.query(DiaryEntry)
        .filter(DiaryEntry.user_id == user.id)
        .order_by(DiaryEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [DiaryOut.model_validate(e) for e in entries]


@router.post("", response_model=DiaryOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_entry(
    request: Request,
    body: DiaryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_pro(user):
        count = db.query(DiaryEntry).filter(DiaryEntry.user_id == user.id).count()
        if count >= DIARY_LIMIT_FREE:
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Free diary limit reached — upgrade to Pro for unlimited entries")

    image_path = None
    if body.image_base64:
        try:
            data = base64.b64decode(body.image_base64)
            image_path = storage.save(data, "diary", "jpg")
        except Exception:
            raise HTTPException(400, "Invalid image_base64")

    entry = DiaryEntry(
        user_id=user.id,
        title=body.title,
        content=body.content,
        occasion=body.occasion,
        look_id=uuid.UUID(body.look_id) if body.look_id else None,
        image_path=image_path,
        score=body.score,
        products_used=[p.model_dump() for p in body.products_used] if body.products_used else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return DiaryOut.model_validate(entry)


@router.get("/{entry_id}", response_model=DiaryOut)
def get_entry(entry_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = db.get(DiaryEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, "Entry not found")
    return DiaryOut.model_validate(entry)


@router.put("/{entry_id}", response_model=DiaryOut)
def update_entry(
    entry_id: uuid.UUID,
    body: DiaryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.get(DiaryEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, "Entry not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return DiaryOut.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = db.get(DiaryEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, "Entry not found")
    if entry.image_path:
        storage.delete(entry.image_path)
    db.delete(entry)
    db.commit()
