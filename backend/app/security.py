"""Jednostavna autentifikacija za demo (potpisani token). U produkciji: SSO / Active Directory."""
import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

settings = get_settings()


def hash_password(pw: str) -> str:
    return hashlib.sha256((settings.secret_key + ":" + pw).encode()).hexdigest()


def make_token(user: User, ttl: int = 7 * 24 * 3600) -> str:
    payload = json.dumps({"uid": user.id, "exp": int(time.time()) + ttl}).encode()
    p = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    sig = hmac.new(settings.secret_key.encode(), p.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{p}.{sig}"


def parse_token(token: str) -> int | None:
    try:
        p, sig = token.split(".")
        good = hmac.new(settings.secret_key.encode(), p.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good):
            return None
        data = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
        if data["exp"] < time.time():
            return None
        return int(data["uid"])
    except Exception:
        return None


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    uid = parse_token(token) if token else None
    user = db.get(User, uid) if uid else None
    if not user or not user.active:
        raise HTTPException(401, "Potrebna je prijava")
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Nemate pravo pristupa")
        return user
    return dep
