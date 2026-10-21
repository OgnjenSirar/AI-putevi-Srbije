"""Drustvene mreze: priprema objave (AI tekst + sablon), AI pozadina, odobrenje i simulirana objava."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SocialPost, User
from ..security import current_user
from ..social import service
from ..social.definitions import BY_CODE, FORMATS, TEMPLATES

router = APIRouter(prefix="/api/social", tags=["mreze"])


def _get(db: Session, pid: int) -> SocialPost:
    p = db.get(SocialPost, pid)
    if not p:
        raise HTTPException(404, "Objava ne postoji")
    return p


@router.get("/templates")
def templates(user: User = Depends(current_user)):
    return {"templates": TEMPLATES, "formats": FORMATS, "imagegen": service.imagegen_status()}


@router.get("/posts")
def posts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [service.post_to_dict(p) for p in db.scalars(select(SocialPost).order_by(SocialPost.id.desc())).all()]


@router.get("/posts/{pid}")
def post(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return service.post_to_dict(_get(db, pid))


class DraftIn(BaseModel):
    brief: str


@router.post("/posts")
def create(body: DraftIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if len(body.brief.strip()) < 10:
        raise HTTPException(400, "Opis objave je prekratak")
    return service.post_to_dict(service.draft_post(db, body.brief.strip(), user.full_name))


class UpdateIn(BaseModel):
    template_code: str
    fields: dict
    fb_text: str
    ig_text: str
    alt_text: str
    image_prompt: str = ""
    remove_background: bool = False


@router.put("/posts/{pid}")
def update(pid: int, body: UpdateIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get(db, pid)
    if p.status == "objavljeno":
        raise HTTPException(400, "Objavljena objava se ne može menjati")
    if body.template_code not in BY_CODE:
        raise HTTPException(400, "Nepoznat šablon")
    p.template_code = body.template_code
    p.fields = service._clean_fields(body.template_code, body.fields)
    p.fb_text, p.ig_text, p.alt_text, p.image_prompt = body.fb_text, body.ig_text, body.alt_text, body.image_prompt
    if body.remove_background:
        p.background, p.background_is_ai = "", False
    p.status = "nacrt"
    db.commit()
    return service.post_to_dict(service.render_with_fit(db, p, max_rounds=0))


class BgIn(BaseModel):
    prompt: str = ""


@router.post("/posts/{pid}/background")
def background(pid: int, body: BgIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get(db, pid)
    try:
        return service.post_to_dict(service.generate_background(db, p, body.prompt or None))
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/posts/{pid}/background-upload")
async def background_upload(pid: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get(db, pid)
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(400, "Fajl je prevelik")
    return service.post_to_dict(service.set_upload_background(db, p, content, file.filename or "slika.jpg"))


@router.post("/posts/{pid}/approve")
def approve(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get(db, pid)
    p.status = "odobreno"
    p.approved_by = user.full_name
    p.approved_at = datetime.now(timezone.utc)
    db.commit()
    return service.post_to_dict(p)


@router.post("/posts/{pid}/publish")
def publish(pid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    p = _get(db, pid)
    if p.status != "odobreno":
        raise HTTPException(400, "Objava mora biti odobrena pre objavljivanja")
    return service.post_to_dict(service.publish_simulated(db, p, user.full_name))
