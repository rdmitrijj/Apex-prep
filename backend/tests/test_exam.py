from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.core.db import SessionLocal
from app.engine.exam import RW_DOMAIN_ORDER, domain_of
from app.models import ExamModule, Question, Response
from app.services.exam import now
from app.services.questions import seed

CREDS = {"email": "exam@example.com", "password": "correct horse battery"}


@pytest.fixture
async def user(client: AsyncClient) -> AsyncClient:
    async with SessionLocal() as db:
        await seed(db)
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 201
    return client


async def _key(qid: int) -> str:
    async with SessionLocal() as db:
        q = await db.get(Question, qid)
        assert q is not None
        return q.content["answer"] if q.format == "mc" else q.content["spr_answers"][0]


async def _wrong(qid: int) -> str:
    async with SessionLocal() as db:
        q = await db.get(Question, qid)
        assert q is not None
        return next(c for c in "ABCD" if c != q.content["answer"]) if q.format == "mc" else "9999"


async def _answer_all(c: AsyncClient, exam_id: int, state: dict, *, right: bool) -> None:
    for item in state["module"]["items"]:
        qid = item["question"]["id"]
        ans = await _key(qid) if right else await _wrong(qid)
        r = await c.put(
            f"/api/exams/{exam_id}/items/{item['id']}",
            json={"answer": ans, "flagged": False, "eliminated": [], "time_ms": 30_000 if right else 200_000},
        )
        assert r.status_code == 204, r.text


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/exams", json={})).status_code == 401
    assert (await client.get("/api/weaknesses")).status_code == 401


async def test_math_exam_routing_scoring_and_review(user: AsyncClient) -> None:
    exam_id = (await user.post("/api/exams", json={"sections": ["MATH"], "difficulty": "hard"})).json()["id"]
    s = (await user.get(f"/api/exams/{exam_id}")).json()
    assert s["total_modules"] == 2 and s["sections"] == ["MATH"]
    assert not s["module"]["started"] and s["module"]["items"] == []  # nothing visible before start

    s = (await user.post(f"/api/exams/{exam_id}/start")).json()
    m = s["module"]
    assert m["section"] == "MATH" and m["stage"] == 1 and len(m["items"]) == 22
    assert 35 * 60_000 - 5_000 < m["remaining_ms"] <= 35 * 60_000
    assert "answer" not in m["items"][0]["question"]
    ratings = [it["question"]["difficulty"] for it in m["items"]]
    order = {"easy": 0, "medium": 1, "hard": 2}
    assert [order[d] for d in ratings] == sorted(order[d] for d in ratings)  # easy → hard

    first = m["items"][0]
    bad = "E" if first["question"]["format"] == "mc" else "3 1/2"
    r = await user.put(f"/api/exams/{exam_id}/items/{first['id']}", json={"answer": bad})
    assert r.status_code == 422
    await _answer_all(user, exam_id, s, right=True)
    flag = {"answer": await _key(first["question"]["id"]), "flagged": True, "eliminated": ["B"], "time_ms": 9}
    await user.put(f"/api/exams/{exam_id}/items/{first['id']}", json=flag)
    resumed = (await user.get(f"/api/exams/{exam_id}")).json()["module"]["items"][0]  # refresh/resume
    assert resumed["flagged"] and resumed["eliminated"] == ["B"] and resumed["time_ms"] == 9

    s = (await user.post(f"/api/exams/{exam_id}/submit-module")).json()
    assert s["module"]["stage"] == 2 and not s["module"]["started"]
    r = await user.put(f"/api/exams/{exam_id}/items/{first['id']}", json={"answer": "A"})
    assert r.status_code == 409  # module 1 is locked
    async with SessionLocal() as db:
        mod2 = await db.scalar(select(ExamModule).where(ExamModule.stage == 2))
        assert mod2 is not None and mod2.route == "harder"

    s = (await user.post(f"/api/exams/{exam_id}/start")).json()
    seen1 = {it["question"]["id"] for it in m["items"]}
    assert not seen1 & {it["question"]["id"] for it in s["module"]["items"]}
    # leave module 2 blank and submit: blanks are wrong
    s = (await user.post(f"/api/exams/{exam_id}/submit-module")).json()
    assert s["status"] == "completed" and s["module"] is None
    again = await user.post(f"/api/exams/{exam_id}/submit-module")  # double submit is harmless
    assert again.status_code == 200

    res = (await user.get(f"/api/exams/{exam_id}/results")).json()
    assert res["rw_score"] is None and 200 <= res["math_score"] <= 800
    assert len(res["items"]) == 44 and sum(i["pretest"] for i in res["items"]) == 4
    assert all(i["key"] for i in res["items"]) and all(i["explanation"] for i in res["items"])
    alg = next(b for b in res["breakdown"] if b["id"] == "MATH.ALG")
    assert alg["total"] == 14 and alg["level"] == "domain"
    blanks = [i for i in res["items"] if i["module"].startswith("Math · Module 2")]
    assert all(i["answer"] is None and not i["correct"] for i in blanks)
    listed = (await user.get("/api/exams")).json()
    assert listed[0]["id"] == exam_id and listed[0]["math_score"] == res["math_score"]


async def test_full_exam_order_break_and_timer_expiry(user: AsyncClient) -> None:
    exam_id = (await user.post("/api/exams", json={})).json()["id"]
    assert (await user.get(f"/api/exams/{exam_id}/results")).status_code == 409
    s = (await user.post(f"/api/exams/{exam_id}/start")).json()
    items = s["module"]["items"]
    assert s["module"]["section"] == "RW" and len(items) == 27
    doms = [RW_DOMAIN_ORDER.index(domain_of(it["question"]["skill_id"])) for it in items]
    assert doms == sorted(doms)

    await _answer_all(user, exam_id, s, right=False)
    # Time runs out: the server closes the module on the next request, without a submit.
    async with SessionLocal() as db:
        await db.execute(
            update(ExamModule)
            .where(ExamModule.section == "RW", ExamModule.stage == 1)
            .values(deadline_at=now() - timedelta(seconds=10))
        )
        await db.commit()
    s = (await user.get(f"/api/exams/{exam_id}")).json()
    assert s["module"]["section"] == "RW" and s["module"]["stage"] == 2 and s["break_remaining_ms"] is None
    async with SessionLocal() as db:
        assert (
            await db.scalar(select(ExamModule.route).where(ExamModule.section == "RW", ExamModule.stage == 2))
        ) == "easier"

    await user.post(f"/api/exams/{exam_id}/start")
    s = (await user.post(f"/api/exams/{exam_id}/submit-module")).json()
    assert s["module"]["section"] == "MATH" and s["module"]["index"] == 3
    assert 9 * 60_000 < s["break_remaining_ms"] <= 10 * 60_000

    # A new exam abandons this one.
    new_id = (await user.post("/api/exams", json={"sections": ["MATH"]})).json()["id"]
    assert [e["id"] for e in (await user.get("/api/exams")).json()] == [new_id]


async def test_weakness_training_targets_exam_misses(user: AsyncClient) -> None:
    exam_id = (await user.post("/api/exams", json={"sections": ["RW"]})).json()["id"]
    s = (await user.post(f"/api/exams/{exam_id}/start")).json()
    await _answer_all(user, exam_id, s, right=False)
    await user.post(f"/api/exams/{exam_id}/submit-module")
    await user.post(f"/api/exams/{exam_id}/start")
    await user.post(f"/api/exams/{exam_id}/submit-module")

    weak = (await user.get("/api/weaknesses?limit=5")).json()
    assert len(weak) == 5 and weak[0]["score"] >= weak[-1]["score"]
    assert all(w["section"] == "RW" and w["attempts"] > 0 for w in weak)  # missed RW beats untried
    assert any("Missed" in r for r in weak[0]["reasons"])
    assert any("slower" in r for w in weak for r in w["reasons"])

    top = {w["skill_id"] for w in (await user.get("/api/weaknesses?limit=8")).json()}
    got = (await user.post("/api/training/next", json={"exclude_ids": []})).json()
    assert got["question"]["skill_id"] in top and got["reasons"]
    r = await user.post(
        "/api/drill/answer",
        json={"question_id": got["question"]["id"], "answer": "A", "time_ms": 5000, "mode": "training"},
    )
    assert r.status_code == 200
    async with SessionLocal() as db:
        assert (await db.scalar(select(Response.mode).where(Response.time_ms == 5000))) == "training"
    math = (await user.post("/api/training/next", json={"section": "MATH"})).json()
    assert math["question"]["skill_id"].startswith("MATH.")


async def test_official_scores_calibrate_exam_estimates(user: AsyncClient) -> None:
    exam_id = (await user.post("/api/exams", json={"sections": ["MATH"]})).json()["id"]
    s = (await user.post(f"/api/exams/{exam_id}/start")).json()
    await _answer_all(user, exam_id, s, right=True)
    await user.post(f"/api/exams/{exam_id}/submit-module")
    await user.post(f"/api/exams/{exam_id}/start")
    await user.post(f"/api/exams/{exam_id}/submit-module")
    before = (await user.get(f"/api/exams/{exam_id}/results")).json()
    assert before["calibrated_with"] == {"MATH": 0} and before["margins"]["MATH"] > 0

    today = now().date().isoformat()
    bad = {"taken_on": today, "rw": 555, "math": 600}
    assert (await user.post("/api/official-scores", json=bad)).status_code == 422
    future = {"taken_on": "2999-01-01", "rw": 550, "math": 600}
    assert (await user.post("/api/official-scores", json=future)).status_code == 422
    # Too far from any in-app exam: stored, but not used for calibration.
    old = {"taken_on": (now() - timedelta(days=40)).date().isoformat(), "rw": 500, "math": 800}
    assert (await user.post("/api/official-scores", json=old)).status_code == 201
    assert (await user.get(f"/api/exams/{exam_id}/results")).json()["math_score"] == before["math_score"]

    target = 300  # far below the uncalibrated estimate, so the shift is unmistakable
    r = await user.post("/api/official-scores", json={"taken_on": today, "rw": 500, "math": target})
    new_id = r.json()["id"]
    after = (await user.get(f"/api/exams/{exam_id}/results")).json()
    assert after["calibrated_with"] == {"MATH": 1}
    assert target <= after["math_score"] < before["math_score"]
    assert after["margins"]["MATH"] < before["margins"]["MATH"]
    listed = (await user.get("/api/official-scores")).json()
    assert listed["calibration"]["MATH"]["pairs"] == 1 and listed["calibration"]["RW"]["pairs"] == 0
    assert listed["scores"][0]["paired_exam"] == {"MATH": exam_id}
    assert listed["scores"][1]["paired_exam"] == {}
    assert (await user.get("/api/exams")).json()[0]["math_score"] == after["math_score"]

    assert (await user.delete(f"/api/official-scores/{new_id}")).status_code == 204
    assert (await user.get(f"/api/exams/{exam_id}/results")).json()["math_score"] == before["math_score"]
