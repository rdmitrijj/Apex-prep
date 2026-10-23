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


# Checked when the account doesn't exist, so response time doesn't reveal which emails are registered.
_DUMMY_HASH = _hasher.hash("no-such-account")


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
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


# ponytail: in-process throttle (failed logins per email, sign-ups per IP); fine for one Render instance,
# move to DB/Redis if scaled out.
_WINDOW_S = 15 * 60
_MAX_ATTEMPTS = 5
_attempts: dict[str, deque[float]] = defaultdict(deque)


def throttled(key: str) -> bool:
    q = _attempts[key]
    while q and q[0] < time.monotonic() - _WINDOW_S:
        q.popleft()
    return len(q) >= _MAX_ATTEMPTS


def record_attempt(key: str) -> None:
    _attempts[key].append(time.monotonic())


def clear_attempts(key: str) -> None:
    _attempts.pop(key, None)
