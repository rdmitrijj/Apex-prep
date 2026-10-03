from httpx import AsyncClient

from app.core import security
from app.core.config import get_settings

CREDS = {"email": "Me@Example.com", "password": "correct horse battery"}


async def test_health(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


async def test_register_login_me_logout(client: AsyncClient) -> None:
    r = await client.post("/api/auth/register", json=CREDS)
    assert r.status_code == 201 and r.json()["email"] == "me@example.com"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie

    assert (await client.get("/api/auth/me")).json()["email"] == "me@example.com"
    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/auth/me")).status_code == 401

    r = await client.post("/api/auth/login", json={**CREDS, "email": "ME@example.com"})
    assert r.status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_duplicate_and_weak_password(client: AsyncClient) -> None:
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 201
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 409
    r = await client.post("/api/auth/register", json={"email": "x@example.com", "password": "short"})
    assert r.status_code == 422


async def test_registration_can_be_locked(client: AsyncClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(get_settings(), "allow_registration", False)
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 403


async def test_bad_token_and_login_throttle(client: AsyncClient) -> None:
    client.cookies.set(security.COOKIE_NAME, "garbage", domain="test")
    assert (await client.get("/api/auth/me")).status_code == 401
    await client.post("/api/auth/register", json=CREDS)
    client.cookies.clear()
    bad = {**CREDS, "password": "wrong password!"}
    for _ in range(5):
        assert (await client.post("/api/auth/login", json=bad)).status_code == 401
    # Even the right password is refused while throttled.
    assert (await client.post("/api/auth/login", json=CREDS)).status_code == 429
    security.clear_login_failures("me@example.com")
