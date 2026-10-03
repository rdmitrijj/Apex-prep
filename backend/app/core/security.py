import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import get_settings

COOKIE_NAME = "apex_session"
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False


def create_token(user_id: int) -> str:
    s = get_settings()
    exp = datetime.now(UTC) + timedelta(days=s.session_days)
    return jwt.encode({"sub": str(user_id), "exp": exp}, s.secret_key, algorithm="HS256")


def decode_token(token: str) -> int | None:
    try:
        return int(jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


# ponytail: in-process login throttle; fine for one Render instance, move to DB/Redis if scaled out.
_FAIL_WINDOW_S = 15 * 60
_MAX_FAILS = 5
_failures: dict[str, deque[float]] = defaultdict(deque)


def login_blocked(email: str) -> bool:
    q = _failures[email]
    while q and q[0] < time.monotonic() - _FAIL_WINDOW_S:
        q.popleft()
    return len(q) >= _MAX_FAILS


def record_login_failure(email: str) -> None:
    _failures[email].append(time.monotonic())


def clear_login_failures(email: str) -> None:
    _failures.pop(email, None)
