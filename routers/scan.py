import base64

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from deps import get_current_user, get_db
from models import ScanReport, User
from plan_limits import SCAN_LIMIT_FREE, is_pro
from schemas import ScanOut
from services import storage
from services.claude import scan_face, scan_nails


def _check_scan_limit(db: Session, user: User, scan_type: str) -> None:
    if is_pro(user):
        return
    count = db.query(ScanReport).filter(ScanReport.user_id == user.id, ScanReport.scan_type == scan_type).count()
    if count >= SCAN_LIMIT_FREE:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"Free {scan_type} scan limit reached — upgrade to Pro for unlimited scans")

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["scan"])


class ScanBody(BaseModel):
    photo_base64: str


@router.post("/scan", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def face_scan(
    request: Request,
    body: ScanBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_scan_limit(db, user, "face")
    try:
        data = base64.b64decode(body.photo_base64)
    except Exception:
        raise HTTPException(400, "Invalid base64 image")

    analysis = scan_face(body.photo_base64)
    image_path = storage.save(data, "scans", "jpg")

    report = ScanReport(user_id=user.id, image_path=image_path, analysis=analysis, scan_type="face")
    db.add(report)
    db.commit()
    db.refresh(report)
    return ScanOut.model_validate(report)


@router.post("/nail-scan", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def nail_scan(
    request: Request,
    body: ScanBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_scan_limit(db, user, "nail")
    try:
        data = base64.b64decode(body.photo_base64)
    except Exception:
        raise HTTPException(400, "Invalid base64 image")

    analysis = scan_nails(body.photo_base64)
    image_path = storage.save(data, "nails", "jpg")

    report = ScanReport(user_id=user.id, image_path=image_path, analysis=analysis, scan_type="nail")
    db.add(report)
    db.commit()
    db.refresh(report)
    return ScanOut.model_validate(report)
