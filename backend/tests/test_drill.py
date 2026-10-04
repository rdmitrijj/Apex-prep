import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Question, Response
from app.services.questions import seed

CREDS = {"email": "drill@example.com", "password": "correct horse battery"}


@pytest.fixture
async def user(client: AsyncClient) -> AsyncClient:
    async with SessionLocal() as db:
        await seed(db)
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 201
    return client


async def _key(qid: int) -> Question:
    async with SessionLocal() as db:
        q = await db.get(Question, qid)
        assert q is not None
        return q


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/skills")).status_code == 401
    assert (await client.post("/api/drill/next", json={"skill_ids": ["MATH"]})).status_code == 401


async def test_math_drill_flow_and_stats(user: AsyncClient) -> None:
    nodes = {n["id"]: n for n in (await user.get("/api/skills")).json()}
    assert nodes["MATH.ALG.LIN1.SOLVE"]["generated"] and nodes["MATH"]["generated"]
    assert not nodes["RW.CAS.WIC.FILL"]["generated"]

    seen = []
    for expect_correct in (True, False):
        r = await user.post(
            "/api/drill/next",
            json={"skill_ids": ["MATH.ALG.LIN1"], "difficulty": "easy", "exclude_ids": seen},
        )
        assert r.status_code == 200, r.text
        q = r.json()
        assert q["skill_id"].startswith("MATH.ALG.LIN1.") and q["difficulty"] == "easy"
        assert "answer" not in q and "explanation" not in q  # nothing leaks before answering
        seen.append(q["id"])
        stored = await _key(q["id"])
        if q["format"] == "mc":
            right = stored.content["answer"]
            given = right if expect_correct else next(c for c in "ABCD" if c != right)
        else:
            given = stored.content["spr_answers"][0] if expect_correct else "99999"
        fb = (
            await user.post(
                "/api/drill/answer", json={"question_id": q["id"], "answer": given, "time_ms": 1234}
            )
        ).json()
        assert fb["correct"] is expect_correct and fb["explanation"]

    nodes = {n["id"]: n for n in (await user.get("/api/skills")).json()}
    assert nodes["MATH.ALG.LIN1"]["attempts"] == 2 and nodes["MATH.ALG.LIN1"]["correct"] == 1
    assert nodes["MATH"]["attempts"] == 2
    async with SessionLocal() as db:
        rows = (await db.scalars(select(Response))).all()
        assert {r.mode for r in rows} == {"drill"} and rows[0].time_ms == 1234


async def test_spr_entry_validation(user: AsyncClient) -> None:
    for _ in range(40):  # generators pick SPR ~30% of the time
        q = (await user.post("/api/drill/next", json={"skill_ids": ["MATH.ALG.LIN1.SOLVE"]})).json()
        if q["format"] == "spr":
            break
    else:
        pytest.fail("no SPR item generated")
    r = await user.post("/api/drill/answer", json={"question_id": q["id"], "answer": "3 1/2", "time_ms": 0})
    assert r.status_code == 422


async def test_empty_rw_skill_and_report(user: AsyncClient) -> None:
    r = await user.post("/api/drill/next", json={"skill_ids": ["NOPE"]})
    assert r.status_code == 422
    q = (await user.post("/api/drill/next", json={"skill_ids": ["MATH.GEO.CIR.ARC"]})).json()
    assert (
        await user.post(f"/api/questions/{q['id']}/report", json={"reason": "figure is wrong"})
    ).status_code == 204
    assert (await _key(q["id"])).status == "quarantined"


async def test_mistakes_notebook_srs_and_tags(user: AsyncClient) -> None:
    from app.models import ReviewSchedule

    q = (await user.post("/api/drill/next", json={"skill_ids": ["MATH.ALG.LIN1.SOLVE"]})).json()
    stored = await _key(q["id"])
    wrong = "9999" if q["format"] == "spr" else next(c for c in "ABCD" if c != stored.content["answer"])
    body = {"question_id": q["id"], "answer": wrong, "time_ms": 10}
    fb = (await user.post("/api/drill/answer", json=body)).json()
    assert fb["correct"] is False and fb["response_id"]
    async with SessionLocal() as db:
        user_id = await db.scalar(select(Response.user_id))
        sched = await db.get(ReviewSchedule, (user_id, q["skill_id"]))
        assert sched is not None and sched.interval_days == 1

    notebook = (await user.get("/api/mistakes")).json()
    assert [m["response_id"] for m in notebook] == [fb["response_id"]]
    assert notebook[0]["key"] and notebook[0]["explanation"] and notebook[0]["answer"] == wrong
    tag = await user.put(f"/api/responses/{fb['response_id']}/reason", json={"miss_reason": "careless"})
    assert tag.status_code == 204
    assert (await user.get("/api/mistakes?reason=careless")).json()[0]["miss_reason"] == "careless"
    assert (await user.get("/api/mistakes?reason=untagged")).json() == []
    assert (await user.get("/api/mistakes?section=RW")).json() == []
    assert len((await user.get("/api/mistakes?skill=MATH.ALG")).json()) == 1
    bad = await user.put(f"/api/responses/{fb['response_id']}/reason", json={"miss_reason": "aliens"})
    assert bad.status_code == 422
