import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    avatar_url: Mapped[str | None] = mapped_column(String)
    token_version: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    plan: Mapped[str] = mapped_column(String, default="free", nullable=False)   # free | pro
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    profile: Mapped["BeautyProfile | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    looks: Mapped[list["Look"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    scan_reports: Mapped[list["ScanReport"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class BeautyProfile(Base):
    __tablename__ = "beauty_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    skin_tone: Mapped[str | None] = mapped_column(String)   # fair / light / medium / tan / deep
    skin_type: Mapped[str | None] = mapped_column(String)   # dry / oily / combination / normal
    undertone: Mapped[str | None] = mapped_column(String)   # warm / cool / neutral
    concerns: Mapped[list] = mapped_column(JSONB, default=list)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped["User"] = relationship(back_populates="profile")


class Look(Base):
    __tablename__ = "looks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    palette: Mapped[dict] = mapped_column(JSONB, nullable=False)   # {lips, blush, eyes, ...}
    zones: Mapped[list] = mapped_column(JSONB, default=list)
    occasion: Mapped[str | None] = mapped_column(String)
    score: Mapped[dict | None] = mapped_column(JSONB)
    thumbnail_path: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="looks")
    diary_entries: Mapped[list["DiaryEntry"]] = relationship(back_populates="look")


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    look_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("looks.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String)
    occasion: Mapped[str | None] = mapped_column(String)
    score: Mapped[float | None] = mapped_column(Float)
    products_used: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped["User"] = relationship(back_populates="diary_entries")
    look: Mapped["Look | None"] = relationship(back_populates="diary_entries")


class ScanReport(Base):
    __tablename__ = "scan_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    image_path: Mapped[str | None] = mapped_column(String)
    analysis: Mapped[dict] = mapped_column(JSONB, nullable=False)
    scan_type: Mapped[str] = mapped_column(String, default="face")   # face | nail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="scan_reports")


class Tutorial(Base):
    __tablename__ = "tutorials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str | None] = mapped_column(String)      # lips / eyes / blush / ...
    difficulty: Mapped[str | None] = mapped_column(String)    # beginner / intermediate / advanced
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    video_url: Mapped[str | None] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Routine(Base):
    __tablename__ = "routines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    morning: Mapped[list] = mapped_column(JSONB, default=list)   # [{step, product, duration_min}]
    evening: Mapped[list] = mapped_column(JSONB, default=list)
    weekly: Mapped[list] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped["User"] = relationship()
