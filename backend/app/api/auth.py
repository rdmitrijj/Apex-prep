from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser
from app.core.config import get_settings
from app.core.security import (
    COOKIE_NAME,
    clear_attempts,
    create_token,
    hash_password,
    record_attempt,
    throttled,
    verify_password,
)
from app.models import StudyPlan, User
from app.schemas.auth import Goals, LoginIn, RegisterIn, UserOut

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
async def register(body: RegisterIn, request: Request, response: Response, db: DB) -> User:
    if not get_settings().allow_registration:
        raise HTTPException(403, "Registration is closed")
    ip = f"register:{request.client.host if request.client else '?'}"
    if throttled(ip):
        raise HTTPException(429, "Too many sign-ups from this network; try again in 15 minutes")
    record_attempt(ip)
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        **body.model_dump(include=set(Goals.model_fields)),
    )
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
    if throttled(email):
        raise HTTPException(429, "Too many failed attempts; try again in 15 minutes")
    user = await db.scalar(select(User).where(func.lower(User.email) == email))
    if not verify_password(user.password_hash if user else None, body.password) or user is None:
        record_attempt(email)
        raise HTTPException(401, "Wrong email or password")
    clear_attempts(email)
    _set_session(response, user)
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, httponly=True, samesite="lax")


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user


@router.put("/me/goals", response_model=UserOut)
async def set_goals(body: Goals, db: DB, user: CurrentUser) -> User:
    for k, v in body.model_dump().items():
        setattr(user, k, v)
    # Stored weekly plans were built for the old goals; the next /plan request rebuilds this week's.
    await db.execute(delete(StudyPlan).where(StudyPlan.user_id == user.id))
    await db.commit()
    return user
