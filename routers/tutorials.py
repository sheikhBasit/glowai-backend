import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import Tutorial, User

router = APIRouter(prefix="/tutorials", tags=["tutorials"])

VALID_CATEGORIES = {
    "lips", "eyes", "blush", "contour", "highlight",
    "brows", "gloss", "liner", "lashes", "skincare", "nails",
}
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


@router.get("")
def list_tutorials(
    category: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    limit: int = Query(default=20, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(400, f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
    if difficulty and difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(400, f"difficulty must be one of: beginner, intermediate, advanced")

    q = db.query(Tutorial)
    if category:
        q = q.filter(Tutorial.category == category)
    if difficulty:
        q = q.filter(Tutorial.difficulty == difficulty)

    return [_fmt(t) for t in q.order_by(Tutorial.sort_order, Tutorial.created_at).limit(limit).all()]


@router.get("/{tutorial_id}")
def get_tutorial(
    tutorial_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.get(Tutorial, tutorial_id)
    if not t:
        raise HTTPException(404, "Tutorial not found")
    return _fmt(t)


def _fmt(t: Tutorial) -> dict:
    import json
    content = t.content
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except Exception:
            content = {}
    content = content or {}
    return {
        "id": str(t.id),
        "title": t.title,
        "category": t.category,
        "difficulty": t.difficulty,
        "video_url": t.video_url,
        "thumbnail": content.get("thumbnail"),
        "channel": content.get("channel"),
        "products": content.get("products", []),
        "steps": content.get("steps", []),
        "content": content,
        "sort_order": t.sort_order,
    }
