from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser
from app.core.config import get_settings
from app.core.security import (
    COOKIE_NAME,
    clear_login_failures,
    create_token,
    hash_password,
    login_blocked,
    record_login_failure,
    verify_password,
)
from app.models import User
from app.schemas.auth import Credentials, LoginIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session(response: Response, user: User) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_token(user.id),
        max_age=get_settings().session_days * 86400,
        httponly=True,
        secure=True,  # browsers accept Secure cookies on http://localhost, so dev works too
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: Credentials, response: Response, db: DB) -> User:
    if not get_settings().allow_registration:
        raise HTTPException(403, "Registration is closed")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(409, "Email already registered") from None
    _set_session(response, user)
    return user


@router.post("/login", response_model=UserOut)
async def login(body: LoginIn, response: Response, db: DB) -> User:
    email = body.email.lower()
    if login_blocked(email):
        raise HTTPException(429, "Too many failed attempts; try again in 15 minutes")
    user = await db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None or not verify_password(user.password_hash, body.password):
        record_login_failure(email)
        raise HTTPException(401, "Wrong email or password")
    clear_login_failures(email)
    _set_session(response, user)
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
