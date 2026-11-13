import json
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.core.db import SessionLocal
from app.models import ImportedMistake, Question, Response, SetReview, User
from app.services import imported, pt5
from app.services.questions import SEED_DIR, seed
from tests.conftest import GOALS

CREDS = {"email": "pt5@example.com", "password": "correct horse battery", **GOALS}
SET = "rw-trans"


@pytest.fixture
async def user(client: AsyncClient) -> AsyncClient:
    async with SessionLocal() as db:
        await seed(db)
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 201
    return client


async def keys() -> dict[int, str]:
    async with SessionLocal() as db:
        rows = await db.scalars(select(Question).where(Question.external_id.like(f"pt5-{SET}-%")))
        return {q.id: q.content["answer"] for q in rows}


async def test_sets_list_rule_card_and_next_order(user: AsyncClient) -> None:
    body = (await user.get("/api/pt5/sets")).json()
    assert {s["id"] for s in body["sets"]} == set(pt5.sets()) and body["readiness"] == 0
    detail = next(s for s in body["sets"] if s["id"] == SET)
    assert all(s["rule"].startswith("# ") for s in body["sets"]) and detail["count"] == 30
    seen: list[int] = []
    diffs = []
    for _ in range(30):
        r = (await user.post(f"/api/pt5/sets/{SET}/next", json={"exclude_ids": seen})).json()
        seen.append(r["question"]["id"])
        diffs.append(r["question"]["difficulty"])
    assert len(set(seen)) == 30 and diffs == sorted(diffs, key=["medium", "hard"].index)
    r = await user.post(f"/api/pt5/sets/{SET}/next", json={"exclude_ids": seen})
    assert r.status_code == 404


async def test_mastery_on_two_days_schedules_review(user: AsyncClient) -> None:
    k = await keys()
    wrong = next(q for q in k)
    miss = (
        await user.post(
            "/api/drill/answer",
            json={"question_id": wrong, "answer": "A" if k[wrong] != "A" else "B", "time_ms": 1},
        )
    ).json()
    assert miss["trap"] and miss["miss_reason"] == "concept"  # named trap + the set's pre-filled tag
    ids = list(k)[1:9]
    for qid in ids:
        r = await user.post("/api/drill/answer", json={"question_id": qid, "answer": k[qid], "time_ms": 1000})
        assert r.json()["correct"]
    s = next(s for s in (await user.get("/api/pt5/sets")).json()["sets"] if s["id"] == SET)
    assert s["recent_correct"] == 8 and not s["mastered"]  # one day only
    async with SessionLocal() as db:  # move the first four answers to yesterday
        old = (await db.scalars(select(Response.id).order_by(Response.id).limit(4))).all()
        yday = datetime.now(UTC) - timedelta(days=1)
        await db.execute(update(Response).where(Response.id.in_(old)).values(created_at=yday))
        await db.commit()
    qid = ids[0]
    await user.post("/api/drill/answer", json={"question_id": qid, "answer": k[qid], "time_ms": 1000})
    body = (await user.get("/api/pt5/sets")).json()
    s = next(s for s in body["sets"] if s["id"] == SET)
    assert s["mastered"] and s["progress"] == 1 and s["review_due_at"] and not s["review_due"]
    assert body["readiness"] == pytest.approx(1 / len(pt5.sets()))
    async with SessionLocal() as db:
        rev = await db.get(SetReview, ((await db.scalar(select(User.id))), SET))
        assert rev is not None and rev.interval_days == 1


async def test_plan_visible_with_pt5_imports_and_checks_persist(user: AsyncClient) -> None:
    plan = (await user.get("/api/pt5/plan")).json()
    assert not plan["visible"] and plan["days"][0]["title"] == "Fri 13"
    async with SessionLocal() as db:
        uid = await db.scalar(select(User.id))
        doc = json.loads((SEED_DIR / "imports" / "bluebook_pt5.json").read_text())
        res = await imported.load(db, uid, doc)
        assert res["mistakes"] == 31
        guessed = await db.scalar(select(ImportedMistake).where(ImportedMistake.result == "guessed"))
        assert guessed is not None
    key = plan["days"][0]["items"][0]["key"]
    assert (await user.put(f"/api/pt5/plan/{key}", json={"done": True})).status_code == 204
    assert (await user.put(f"/api/pt5/plan/{key}", json={"done": True})).status_code == 204  # idempotent
    plan = (await user.get("/api/pt5/plan")).json()
    assert plan["visible"] and plan["days"][0]["items"][0]["done"]
    await user.put(f"/api/pt5/plan/{key}", json={"done": False})
    assert not (await user.get("/api/pt5/plan")).json()["days"][0]["items"][0]["done"]
    assert (await user.put("/api/pt5/plan/nope", json={"done": True})).status_code == 404


async def test_mini_mock_forms_start_in_order_and_record_the_form(user: AsyncClient) -> None:
    for mode, n, limit in (("mockrw", 27, 32 * 60), ("mockmath", 22, 35 * 60)):
        r = await user.post("/api/triage/start", json={"mode": mode, "form": "A"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["questions"]) == n and body["limit_seconds"] == limit and body["form"] == "A"
    qs = body["questions"]
    async with SessionLocal() as db:
        ids = [q["question"]["id"] for q in qs]
        eids = set(await db.scalars(select(Question.external_id).where(Question.id.in_(ids))))
    assert eids == set(pt5.forms()["A"]["math"])
    rw = (await user.post("/api/triage/start", json={"mode": "mockrw", "form": "B"})).json()["questions"]
    order = ["RW.CAS", "RW.INI", "RW.SEC", "RW.EOI"]
    doms = [order.index(".".join(q["question"]["skill_id"].split(".")[:2])) for q in rw]
    assert doms == sorted(doms)
    items = [{"question_id": q["question"]["id"], "answer": None, "time_ms": 0} for q in qs]
    r = await user.post(
        "/api/triage/sessions", json={"mode": "mockmath", "form": "A", "elapsed_ms": 1000, "items": items}
    )
    assert r.status_code == 200 and r.json()["mode"] == "mockmath-A" and r.json()["blanks"] == 22


async def test_mock_only_items_never_reach_drills(user: AsyncClient) -> None:
    async with SessionLocal() as db:
        mock = (await db.scalars(select(Question).where(Question.external_id.like("pt5-mock-%")))).all()
    skills = sorted({q.skill_id for q in mock})
    seen: list[int] = []
    for _ in range(60):
        r = await user.post("/api/drill/next", json={"skill_ids": skills, "exclude_ids": seen[-200:]})
        if r.status_code != 200:
            break
        seen.append(r.json()["id"])
    assert not {q.id for q in mock} & set(seen)
