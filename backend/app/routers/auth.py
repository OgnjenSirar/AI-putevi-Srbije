import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import (SESSION_COOKIE, current_user, hash_password, make_token, user_from_cookie,
                        verify_password)

TOKEN_TTL = 7 * 24 * 3600

router = APIRouter(prefix="/api/auth", tags=["prijava"])


def user_dict(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role,
            "org_unit": {"id": u.org_unit.id, "code": u.org_unit.code, "name": u.org_unit.name} if u.org_unit else None}


class LoginIn(BaseModel):
    username: str
    password: str


def _set_session(response: Response, request: Request, token: str) -> None:
    """Kolacic sesije: njime nginx proverava pristup slikama (/media) i Mailpit-u (/mailpit)."""
    response.set_cookie(SESSION_COOKIE, token, max_age=TOKEN_TTL, httponly=True, samesite="lax", path="/",
                        secure=request.headers.get("x-forwarded-proto", request.url.scheme) == "https")


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.username == body.username.strip().lower()))
    if not u or not u.active or not verify_password(body.password, u.password_hash):
        time.sleep(0.8)  # usporava pogadjanje lozinki (nginx dodatno ogranicava broj pokusaja)
        raise HTTPException(401, "Pogrešno korisničko ime ili lozinka")
    if not u.password_hash.startswith("pbkdf2$"):
        u.password_hash = hash_password(body.password)
        db.commit()
    token = make_token(u, TOKEN_TTL)
    _set_session(response, request, token)
    return {"token": token, "user": user_dict(u)}


@router.get("/me")
def me(request: Request, response: Response, user: User = Depends(current_user)):
    # Obnavlja kolacic sesije i za korisnike prijavljene pre uvodjenja kolacica
    token = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    if token:
        _set_session(response, request, token)
    return user_dict(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/check", include_in_schema=False)
def check(request: Request, db: Session = Depends(get_db)):
    """Interna provera za nginx auth_request: 204 ako je kolacic sesije ispravan, inace 401."""
    if not user_from_cookie(request, db):
        raise HTTPException(401, "Potrebna je prijava")
    return Response(status_code=204)
