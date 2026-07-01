from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import DiaryEntry, Look, ScanReport, User

router = APIRouter(prefix="/glow-journey", tags=["glow-journey"])


@router.get("")
def glow_journey(
    days: int = Query(default=30, le=365),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    looks = db.query(Look).filter(Look.user_id == user.id).order_by(Look.created_at.desc()).all()
    recent_looks = [l for l in looks if l.created_at.replace(tzinfo=timezone.utc) >= since]
    diary = db.query(DiaryEntry).filter(DiaryEntry.user_id == user.id).all()
    scans = db.query(ScanReport).filter(ScanReport.user_id == user.id).all()
    face_scans = [s for s in scans if s.scan_type == "face"]
    nail_scans = [s for s in scans if s.scan_type == "nail"]

    # Scores from looks
    scored = [l for l in looks if l.score and "overall" in l.score]
    avg_score = round(sum(l.score["overall"] for l in scored) / len(scored), 1) if scored else None
    total_score = round(sum(l.score["overall"] for l in scored), 1)

    # Occasion breakdown
    occasions: dict[str, int] = {}
    for l in looks:
        if l.occasion:
            occasions[l.occasion] = occasions.get(l.occasion, 0) + 1

    # Most used lip colour
    lip_counts: dict[str, int] = {}
    for l in looks:
        lip = l.palette.get("lips") if l.palette else None
        if lip:
            lip_counts[lip] = lip_counts.get(lip, 0) + 1
    top_lip = max(lip_counts, key=lip_counts.get) if lip_counts else None

    # Activity streak (consecutive days with at least one look/diary/scan)
    all_days = set()
    for l in looks:
        all_days.add(l.created_at.date())
    for e in diary:
        all_days.add(e.created_at.date())
    for s in scans:
        all_days.add(s.created_at.date())

    streak = 0
    check = datetime.now(timezone.utc).date()
    while check in all_days:
        streak += 1
        check -= timedelta(days=1)

    # Recent looks for feed
    feed = []
    for l in looks[:10]:
        feed.append({
            "id": str(l.id),
            "type": "look",
            "name": l.name,
            "occasion": l.occasion,
            "score": l.score.get("overall") if l.score else None,
            "palette_preview": list(l.palette.values())[:3] if l.palette else [],
            "created_at": l.created_at.isoformat(),
        })

    return {
        "period_days": days,
        "stats": {
            "total_looks": len(looks),
            "looks_this_period": len(recent_looks),
            "total_diary": len(diary),
            "total_scans": len(face_scans),
            "total_nail_scans": len(nail_scans),
            "average_score": avg_score,
            "total_score": total_score,
            "activity_streak_days": streak,
            "top_lip_color": top_lip,
        },
        "occasions": occasions,
        "recent_feed": feed,
    }
