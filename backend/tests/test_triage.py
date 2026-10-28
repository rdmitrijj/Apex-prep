import random
from collections import Counter
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.engine import triage as tr
from app.models import Question, Response, TriageSession
from app.services.questions import seed
from tests.conftest import GOALS

CREDS = {"email": "triage@example.com", "password": "correct horse battery", **GOALS}
WIC, CTC, BND = "RW.CAS.WIC.FILL", "RW.CAS.CTC.RESPONSE", "RW.SEC.BND.LINK"


def test_soft_timer_turns_amber_at_target_and_red_30s_later() -> None:
    assert tr.timer_color(49.9, 50) == "normal"
    assert tr.timer_color(50, 50) == "amber"
    assert tr.timer_color(79.9, 50) == "amber"
    assert tr.timer_color(80, 50) == "red"
    assert tr.target_seconds(WIC) == 50 and tr.target_seconds(CTC) == 90 and tr.target_seconds(BND) == 40
    assert tr.target_seconds("MATH.ALG.LIN1.SOLVE") == tr.MATH_TARGET


def test_plans_match_mode_sizes_and_weights() -> None:
    rng = random.Random(1)
    sprint = tr.plan("sprint", [], rng)
    assert len(sprint) == 12 and {s.difficulty for s in sprint} == {"hard"}
    assert Counter(s.prefix for s in sprint) == {"RW.INI": 4, "RW.CAS": 4, "RW.SEC": 2, "RW.EOI": 2}
    module = tr.plan("module", [], rng)
    assert len(module) == 27
    assert Counter(s.difficulty for s in module) == {"hard": 22, "medium": 5}
    assert Counter(s.prefix for s in module) == {"RW.INI": 10, "RW.CAS": 8, "RW.SEC": 5, "RW.EOI": 4}
    weak = tr.plan("weakness", ["RW.CAS.WIC", "RW.INI.COET", "RW.SEC.BND"], rng)
    assert Counter(s.prefix for s in weak) == {"RW.CAS.WIC": 5, "RW.INI.COET": 5}
    assert len(tr.plan("math", [], rng)) == 10


def test_analysis_time_sinks_passes_and_recommendations() -> None:
    items = [
        tr.Item(CTC, False, False, 150, True),  # over 90 s and wrong: time sink
        tr.Item(CTC, False, False, 130, True),  # time sink
        tr.Item(CTC, True, False, 140, False),  # slow but right: not a sink
        tr.Item(WIC, True, False, 30, True),
        tr.Item(WIC, False, False, 20, True),  # fast miss: not a sink
        tr.Item(WIC, False, False, 25, False),
        tr.Item(BND, False, True, 0, True),  # blank
    ]
    a = tr.analyze(items, {"RW.CAS.CTC": "Cross-Text Connections", "RW.CAS.WIC": "Words in Context"})
    assert (a.total, a.correct, a.blanks) == (7, 2, 1)
    assert a.time_sinks == {"RW.CAS.CTC": 2}
    assert a.first_pass == (1, 4) and a.second_pass == (1, 2)  # blanks count in neither pass
    ctc = next(g for g in a.by_skill if g.id == "RW.CAS.CTC")
    assert (ctc.total, ctc.correct, ctc.avg_seconds, ctc.target_seconds) == (3, 1, 140, 90)
    assert [g.id for g in a.by_domain] == ["RW.CAS", "RW.SEC"]
    assert len(a.recommendations) == 3
    assert a.recommendations[0].startswith("Cross-Text Connections took 140 s on average (target 90 s)")
    assert any("predict your own word" in r for r in a.recommendations)
    assert any("left 1 blank" in r for r in a.recommendations)
    assert tr.analyze([tr.Item(WIC, True, False, 30, True)], {}).recommendations == []


@pytest.fixture
async def user(client: AsyncClient) -> AsyncClient:
    async with SessionLocal() as db:
        await seed(db)
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 201
    return client


async def test_start_every_mode(user: AsyncClient) -> None:
    for mode, n in (("sprint", 12), ("module", 27), ("weakness", 10), ("math", 10)):
        r = await user.post("/api/triage/start", json={"mode": mode})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["questions"]) == n and body["limit_seconds"] == tr.MODES[mode][1]
        assert len({q["question"]["id"] for q in body["questions"]}) == n
        assert "answer" not in body["questions"][0]["question"]
    module = (await user.post("/api/triage/start", json={"mode": "module"})).json()["questions"]
    domains = [".".join(q["question"]["skill_id"].split(".")[:2]) for q in module]
    order = ["RW.CAS", "RW.INI", "RW.SEC", "RW.EOI"]  # official order, grouped
    assert [order.index(d) for d in domains] == sorted(order.index(d) for d in domains)


async def test_submit_grades_tags_and_records_history(user: AsyncClient) -> None:
    qs = (await user.post("/api/triage/start", json={"mode": "sprint"})).json()["questions"]
    async with SessionLocal() as db:
        keys = {q.id: q.content["answer"] for q in await db.scalars(select(Question))}
    wrong = lambda k: "A" if k != "A" else "B"  # noqa: E731
    items = [
        {"question_id": qs[0]["question"]["id"], "answer": keys[qs[0]["question"]["id"]], "time_ms": 30_000},
        {
            "question_id": qs[1]["question"]["id"],
            "answer": wrong(keys[qs[1]["question"]["id"]]),
            "time_ms": 200_000,
        },
        {"question_id": qs[2]["question"]["id"], "answer": None, "time_ms": 0},
        {
            "question_id": qs[3]["question"]["id"],
            "answer": keys[qs[3]["question"]["id"]].lower(),
            "time_ms": 5_000,
            "first_pass": False,
            "flagged": True,
        },
    ]
    r = await user.post(
        "/api/triage/sessions", json={"mode": "sprint", "elapsed_ms": 400_000, "items": items}
    )
    assert r.status_code == 200, r.text
    res = r.json()
    assert (res["total"], res["correct"], res["blanks"]) == (4, 2, 1)
    assert res["first_pass"] == [1, 2] and res["second_pass"] == [1, 1]
    assert [i["time_sink"] for i in res["items"]] == [False, True, False, False]
    assert sum(s["count"] for s in res["time_sinks"]) == 1
    assert any("left 1 blank" in t for t in res["recommendations"])
    async with SessionLocal() as db:
        rows = (
            await db.scalars(select(Response).where(Response.mode == "triage").order_by(Response.id))
        ).all()
        assert [(x.correct, x.miss_reason) for x in rows] == [
            (True, None),
            (False, "slow"),
            (False, "slow"),
            (True, None),
        ]
        assert rows[2].answer is None and await db.scalar(select(TriageSession.total)) == 4
    misses = (await user.get("/api/mistakes", params={"mode": "triage"})).json()
    assert len(misses) == 2
    hist = (await user.get("/api/triage/sessions")).json()
    assert len(hist) == 1 and hist[0]["blanks"] == 1 and hist[0]["elapsed_seconds"] == 400


async def test_submit_rejects_bad_input(user: AsyncClient) -> None:
    qid = (await user.post("/api/triage/start", json={"mode": "sprint"})).json()["questions"][0]["question"][
        "id"
    ]
    item = {"question_id": qid, "answer": "A", "time_ms": 1000}

    def post(items: list[dict[str, object]]) -> Any:
        return user.post("/api/triage/sessions", json={"mode": "sprint", "elapsed_ms": 1, "items": items})

    assert (await post([item, item])).status_code == 422
    assert (await post([{**item, "answer": "AB"}])).status_code == 422
    assert (await post([{**item, "question_id": 10**9}])).status_code == 404
