from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import Routine, User

router = APIRouter(prefix="/routine", tags=["routine"])


class RoutineStep(BaseModel):
    step: str
    product: str | None = None
    duration_min: int | None = None


class RoutineBody(BaseModel):
    morning: list[RoutineStep] = []
    evening: list[RoutineStep] = []
    weekly: list[RoutineStep] = []
    notes: str | None = None


def _fmt(r: Routine) -> dict:
    return {
        "id": str(r.id),
        "morning": r.morning,
        "evening": r.evening,
        "weekly": r.weekly,
        "notes": r.notes,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("")
def get_routine(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Routine).filter(Routine.user_id == user.id).first()
    if not r:
        return {"morning": [], "evening": [], "weekly": [], "notes": None, "updated_at": None}
    return _fmt(r)


@router.put("")
def upsert_routine(body: RoutineBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Routine).filter(Routine.user_id == user.id).first()
    data = body.model_dump()
    if r:
        r.morning = data["morning"]
        r.evening = data["evening"]
        r.weekly = data["weekly"]
        r.notes = data["notes"]
    else:
        r = Routine(user_id=user.id, **data)
        db.add(r)
    db.commit()
    db.refresh(r)
    return _fmt(r)
