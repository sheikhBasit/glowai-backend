import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

import auth as auth_utils
from deps import get_current_user, get_db
from models import User
from schemas import AccessTokenResponse, AuthResponse, LoginRequest, RefreshRequest, SignupRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=body.email, password_hash=auth_utils.hash_password(body.password), name=body.name)
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
    user = db.query(User).filter(User.email == body.email).first()
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
