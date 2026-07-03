import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

import auth as auth_utils
from deps import get_current_user, get_db
from models import User
from schemas import (
    AccessTokenResponse,
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    UserOut,
)
from services.email import send_password_reset_code

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

RESET_CODE_TTL_MINUTES = 15


def _hash_reset_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=email, password_hash=auth_utils.hash_password(body.password), name=body.name)
    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        access_token=auth_utils.create_access_token(str(user.id), user.token_version),
        refresh_token=auth_utils.create_refresh_token(str(user.id), user.token_version),
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == body.email.strip().lower()).first()
    if not user or not auth_utils.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return AuthResponse(
        access_token=auth_utils.create_access_token(str(user.id), user.token_version),
        refresh_token=auth_utils.create_refresh_token(str(user.id), user.token_version),
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        user_id, token_version = auth_utils.decode_refresh_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user.token_version != token_version:
        raise HTTPException(status_code=401, detail="Token revoked — please log in again")

    return AccessTokenResponse(access_token=auth_utils.create_access_token(str(user.id), user.token_version))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/hour")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == body.email.strip().lower()).first()
    if user:
        code = f"{secrets.randbelow(1_000_000):06d}"
        user.reset_code_hash = _hash_reset_code(code)
        user.reset_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES)
        db.commit()
        send_password_reset_code(user.email, code)
    # Always 204, whether or not the email is registered — don't leak account existence.


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/hour")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == body.email.strip().lower()).first()
    if (
        not user
        or not user.reset_code_hash
        or not user.reset_code_expires_at
        or user.reset_code_expires_at < datetime.now(timezone.utc)
        or user.reset_code_hash != _hash_reset_code(body.code)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user.password_hash = auth_utils.hash_password(body.new_password)
    user.reset_code_hash = None
    user.reset_code_expires_at = None
    user.token_version += 1  # invalidate all existing sessions
    db.commit()
