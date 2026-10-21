from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import current_user
from ..services import reports

router = APIRouter(prefix="/api/reports", tags=["izvestaji"])

MIME = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf"}


@router.get("/summary")
def summary(days: int = 30, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return {"rad": reports.summary(db, days), "ai": reports.ai_metrics(db, days), "trosak": reports.ai_cost(db, days)}


@router.get("/audit")
def audit(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return reports.audit(db)


@router.get("/export/{fmt}")
def export(fmt: str, days: int = 30, db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = {"xlsx": reports.export_xlsx, "docx": reports.export_docx, "pdf": reports.export_pdf}[fmt](db, days)
    return Response(content=data, media_type=MIME[fmt],
                    headers={"Content-Disposition": f'attachment; filename="izvestaj-korisnicki-centar-{days}d.{fmt}"'})
