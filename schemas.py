import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    plan: str
    plan_expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Beauty Profile ─────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    skin_tone: str | None = None
    skin_type: str | None = None
    undertone: str | None = None
    concerns: list[str] | None = None
    preferences: dict[str, Any] | None = None

class ProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    skin_tone: str | None
    skin_type: str | None
    undertone: str | None
    concerns: list
    preferences: dict
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Looks ──────────────────────────────────────────────────────────────────────

class LookCreate(BaseModel):
    name: str
    palette: dict[str, str]   # zone → hex
    zones: list[str] = []
    occasion: str | None = None
    score: dict | None = None

class LookOut(BaseModel):
    id: uuid.UUID
    name: str
    palette: dict
    zones: list
    occasion: str | None
    score: dict | None
    thumbnail_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Diary ──────────────────────────────────────────────────────────────────────

class DiaryCreate(BaseModel):
    title: str
    content: str | None = None
    look_id: uuid.UUID | None = None
    occasion: str | None = None

class DiaryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    occasion: str | None = None

class DiaryOut(BaseModel):
    id: uuid.UUID
    title: str
    content: str | None
    image_path: str | None
    look_id: uuid.UUID | None
    occasion: str | None
    score: float | None
    products_used: list[dict] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Scan ───────────────────────────────────────────────────────────────────────

class ScanOut(BaseModel):
    id: uuid.UUID
    scan_type: str
    analysis: dict
    image_path: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI endpoints ───────────────────────────────────────────────────────────────


class AiLookRequest(BaseModel):
    arB64: str
    activeZones: list[str] = []
    colors: dict[str, str] = {}
    occasion: str = "Everyday"
    skinTone: str | None = None
    undertone: str | None = None

class AiLookResponse(BaseModel):
    zones: list[str]           # which zones to activate
    colors: dict[str, str]     # zone → hex color
    analysis: str
    applied: list[str]
    why: str
    score: float               # 0-10 match score for occasion + features

class ScoreRequest(BaseModel):
    photo_base64: str
    occasion: str = "Everyday"
    makeup: dict[str, str | None] = {}

class ScoreResponse(BaseModel):
    overall: float
    color_harmony: float
    skin_match: float
    occasion_match: float
    vibe: str
    tip: str
    recommendation: str
