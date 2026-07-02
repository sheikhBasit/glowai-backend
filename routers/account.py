import base64

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

import auth as auth_utils
from deps import get_current_user, get_db
from models import User
from services import storage

router = APIRouter(prefix="/account", tags=["account"])


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_enough(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UpdateNameBody(BaseModel):
    name: str


class UpdateAvatarBody(BaseModel):
    image_base64: str


@router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not auth_utils.verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = auth_utils.hash_password(body.new_password)
    user.token_version += 1  # invalidate all existing sessions
    db.commit()


@router.patch("/name")
def update_name(
    body: UpdateNameBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.name = body.name.strip()
    db.commit()
    db.refresh(user)
    return {"id": str(user.id), "name": user.name, "email": user.email}


@router.patch("/avatar")
def update_avatar(
    body: UpdateAvatarBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = base64.b64decode(body.image_base64)
        avatar_path = storage.save(data, "avatars", "jpg")
    except Exception:
        raise HTTPException(400, "Invalid image_base64")

    if user.avatar_url:
        storage.delete(user.avatar_url)

    user.avatar_url = avatar_path
    db.commit()
    db.refresh(user)
    return {"id": str(user.id), "avatar_url": user.avatar_url}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
