from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import current_user, hash_password, make_token

router = APIRouter(prefix="/api/auth", tags=["prijava"])


def user_dict(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role,
            "org_unit": {"id": u.org_unit.id, "code": u.org_unit.code, "name": u.org_unit.name} if u.org_unit else None}


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    if not u or not u.active or u.password_hash != hash_password(body.password):
        raise HTTPException(401, "Pogrešno korisničko ime ili lozinka")
    return {"token": make_token(u), "user": user_dict(u)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_dict(user)


@router.get("/demo-users")
def demo_users(db: Session = Depends(get_db)):
    """Lista naloga za brzu prijavu na demo ekranu (lozinka za sve je 'demo')."""
    return [user_dict(u) for u in db.scalars(select(User).where(User.active.is_(True)).order_by(User.id)).all()]
