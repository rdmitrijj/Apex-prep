import json
from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.core.db import SessionLocal
from app.models import ImportedMistake, OfficialScore, Question, Response, User
from app.services import imported
from app.services.questions import SEED_DIR, seed
from tests.conftest import GOALS

CREDS = {"email": "pt4@example.com", "password": "correct horse battery", **GOALS}
DOC = json.loads((SEED_DIR / "imports" / "bluebook_pt4.json").read_text())


@pytest.fixture
async def user(client: AsyncClient) -> AsyncClient:
    async with SessionLocal() as db:
        await seed(db)
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 201
    async with SessionLocal() as db:
        uid = await db.scalar(select(User.id).where(User.email == CREDS["email"]))
        assert uid is not None
        assert await imported.load(db, uid, DOC) == {"mistakes": 33, "added": 33, "score_logged": 1}
        assert await imported.load(db, uid, DOC) == {"mistakes": 33, "added": 0, "score_logged": 0}
    return client


def _key(q: Question) -> str:
    return q.content["answer"] if q.format == "mc" else q.content["spr_answers"][0]


async def _answer_twins(client: AsyncClient, twin_ids: list[int]) -> None:
    for qid in twin_ids:
        async with SessionLocal() as db:
            q = await db.get(Question, qid)
            assert q is not None
        r = await client.post(
            "/api/drill/answer", json={"question_id": qid, "answer": _key(q), "time_ms": 1000}
        )
        assert r.json()["correct"], q.content["stem"]


async def test_import_shows_up_and_retires_after_two_days(user: AsyncClient) -> None:
    rows = (await user.get("/api/imported-mistakes")).json()
    assert len(rows) == 33 and all(r["due"] and len(r["twin_ids"]) == 3 for r in rows)
    first = rows[0]
    assert first["badge"] == "Bluebook PT4" and first["external_id"] == "bb-pt4-rw-m1-q01"
    assert first["where_to_review"].endswith("Reading and Writing Module 1 Q1")
    twins = (await user.get(f"/api/imported-mistakes/{first['id']}/twins")).json()
    assert [t["id"] for t in twins] == first["twin_ids"] and "passage" in twins[0]

    async with SessionLocal() as db:
        assert await db.scalar(select(OfficialScore.rw).where(OfficialScore.label == DOC["label"])) == 480

    weak = {w["skill_id"]: w for w in (await user.get("/api/weaknesses?limit=100")).json()}
    assert weak["RW.CAS.WIC.FILL"]["attempts"] == 6 and "Due for review" in weak["RW.CAS.WIC.FILL"]["reasons"]

    await _answer_twins(user, first["twin_ids"])
    async with SessionLocal() as db:
        m = await db.get(ImportedMistake, first["id"])
        assert m is not None and m.retired_at is None and m.interval_days == 1
        # pretend those answers were given yesterday
        await db.execute(
            update(Response)
            .where(Response.question_id.in_(first["twin_ids"]))
            .values(created_at=Response.created_at - timedelta(days=1))
        )
        await db.commit()
    await _answer_twins(user, first["twin_ids"])
    rows = {r["id"]: r for r in (await user.get("/api/imported-mistakes")).json()}
    assert rows[first["id"]]["retired"] and not rows[first["id"]]["due"]
    assert len((await user.get("/api/imported-mistakes?due=true")).json()) == 32

    r = await user.put(f"/api/imported-mistakes/{first['id']}/reason", json={"miss_reason": "careless"})
    assert r.status_code == 204
