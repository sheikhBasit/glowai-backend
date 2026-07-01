import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import ScanReport, User
from schemas import ScanOut

router = APIRouter(prefix="/scans", tags=["scans"])


@router.get("", response_model=list[ScanOut])
def list_scans(
    scan_type: str | None = None,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ScanReport).filter(ScanReport.user_id == user.id)
    if scan_type:
        q = q.filter(ScanReport.scan_type == scan_type)
    reports = q.order_by(ScanReport.created_at.desc()).limit(limit).all()
    return [ScanOut.model_validate(r) for r in reports]


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(ScanReport, scan_id)
    if not report or report.user_id != user.id:
        raise HTTPException(404, "Scan report not found")
    return ScanOut.model_validate(report)
