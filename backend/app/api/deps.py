from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import COOKIE_NAME, decode_token
from app.models import User

DB = Annotated[AsyncSession, Depends(get_session)]


async def current_user(db: DB, token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None) -> User:
    user_id = decode_token(token) if token else None
    user = await db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(401, "Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
