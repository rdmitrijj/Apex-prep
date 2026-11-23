import json
from fractions import Fraction

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.generators.spr import is_correct
from app.models import Question, User
from app.schemas.question import MathItem, RWSeedItem
from app.services import imported
from app.services.questions import SEED_DIR, seed
from app.validate import check_pt6
from tests.conftest import GOALS

CREDS = {"email": "pt6@example.com", "password": "correct horse battery", **GOALS}
SOURCE = json.loads((SEED_DIR / "pt6" / "source" / "pt6_mistakes.json").read_text())["mistakes"]


@pytest.fixture
async def user(client: AsyncClient) -> AsyncClient:
    async with SessionLocal() as db:
        await seed(db)
    assert (await client.post("/api/auth/register", json=CREDS)).status_code == 201
    return client


def label(r: dict[str, object]) -> str:
    return f"PT6 · {'R&W' if r['section'] == 'rw' else 'Math'} M{r['module']} · Q{r['number']}"


async def ids_by_external() -> dict[str, int]:
    async with SessionLocal() as db:
        rows = await db.execute(
            select(Question.external_id, Question.id).where(Question.external_id.like("pt6-%"))
        )
        return {e: i for e, i in rows.all()}


async def test_replay_is_in_test_order_with_labels(user: AsyncClient) -> None:
    body = (await user.get("/api/pt6/replay")).json()
    assert [q["label"] for q in body] == [label(r) for r in SOURCE]  # the source file is in test order
    assert len((await user.get("/api/pt6/replay?section=rw")).json()) == 25
    assert len((await user.get("/api/pt6/replay?section=math")).json()) == 10
    assert all("answer" not in q and "replay" not in q for q in body)  # no key before answering


async def test_practice_feedback_names_the_same_trap(user: AsyncClient) -> None:
    ids = await ids_by_external()
    rec = next(r for r in SOURCE if r["external_id"] == "pt6-rw-m2-q12")

    async def answer(eid: str, a: str) -> dict[str, object]:
        r = await user.post("/api/drill/answer", json={"question_id": ids[eid], "answer": a, "time_ms": 1})
        assert r.status_code == 200, r.text
        return r.json()

    fb = await answer("pt6-replay-rw-m2-q12", rec["my_answer"])
    assert not fb["correct"] and fb["same_trap"] == rec["trap"] and fb["lesson"] == rec["lesson"]
    fb = await answer("pt6-replay-rw-m2-q12", "B")  # a different wrong answer
    assert not fb["correct"] and fb["same_trap"] is None and fb["trap"]
    fb = await answer("pt6-replay-rw-m2-q12", rec["correct_answer"])
    assert fb["correct"] and fb["same_trap"] is None and fb["lesson"] == rec["lesson"]
    # SPR: traps are matched by value, and the PT6 trap value is flagged.
    fb = await answer("pt6-replay-math-m1-q19", "75")
    assert not fb["correct"] and fb["same_trap"] and fb["trap"].startswith("Flipped ratio")
    fb = await answer("pt6-replay-math-m1-q14", "6/2")
    assert fb["same_trap"] and "whisker" in fb["trap"]
    assert (await answer("pt6-replay-math-m2-q19", "3.333"))["correct"]
    # Blanks in PT6 have no "same trap".
    assert (await answer("pt6-replay-math-m2-q17", "14"))["same_trap"] is None


async def test_replay_timed_modes_keep_order_and_record_blanks(user: AsyncClient) -> None:
    for mode, n, limit in (("replayrw", 25, 30 * 60), ("replaymath", 10, 16 * 60)):
        r = await user.post("/api/triage/start", json={"mode": mode})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["questions"]) == n and body["limit_seconds"] == limit
    labels = [q["question"]["label"] for q in body["questions"]]
    assert labels == [label(r) for r in SOURCE if r["section"] == "math"]
    items = [{"question_id": q["question"]["id"], "answer": None, "time_ms": 0} for q in body["questions"]]
    res = (
        await user.post(
            "/api/triage/sessions", json={"mode": "replaymath", "elapsed_ms": 1000, "items": items}
        )
    ).json()
    assert res["mode"] == "replaymath" and res["blanks"] == 10


async def test_import_keeps_trap_links_twins_and_is_due(user: AsyncClient) -> None:
    doc = json.loads((SEED_DIR / "imports" / "bluebook_pt6.json").read_text())
    async with SessionLocal() as db:
        uid = await db.scalar(select(User.id).where(User.email == CREDS["email"]))
        assert uid is not None
        assert (await imported.load(db, uid, doc))["added"] == 35
        assert (await imported.load(db, uid, doc))["added"] == 0  # idempotent
    due = (await user.get("/api/imported-mistakes?due=true")).json()
    assert len(due) == 35 and all(m["trap"] and len(m["twin_ids"]) >= 3 for m in due)
    assert {m["miss_reason"] for m in due if m["result"] == "omitted"} == {"slow"}
    assert due[0]["badge"] == "Bluebook PT6"


def items() -> dict[str, RWSeedItem | MathItem]:
    out: dict[str, RWSeedItem | MathItem] = {}
    for f in sorted((SEED_DIR / "rw").glob("pt6_*.json")):
        out |= {i["id"]: RWSeedItem.model_validate(i) for i in json.loads(f.read_text())}
    for f in sorted((SEED_DIR / "math").glob("pt6_*.json")):
        out |= {i["id"]: MathItem.model_validate(i) for i in json.loads(f.read_text())}
    return out


def test_mirror_originality_and_box_plot_checks() -> None:
    good = items()
    assert check_pt6(good) == []
    bad = dict(good)
    bad["pt6-replay-rw-m2-q12"] = good["pt6-replay-rw-m2-q12"].model_copy(update={"answer": "A"})
    q16 = good["pt6-replay-rw-m2-q16"]
    assert q16.replay is not None
    bad["pt6-replay-rw-m2-q16"] = q16.model_copy(
        update={"replay": q16.replay.model_copy(update={"trap_answer": "A"})}
    )
    echo = next(r["paraphrase"] for r in SOURCE if r["external_id"] == "pt6-rw-m1-q14")
    q14 = good["pt6-replay-rw-m1-q14"]
    assert isinstance(q14, RWSeedItem)
    bad["pt6-replay-rw-m1-q14"] = q14.model_copy(update={"passage": q14.passage + " " + echo})
    box = good["pt6-replay-math-m1-q14"]
    assert isinstance(box, MathItem) and box.figure is not None
    plots = [dict(p) for p in box.figure["plots"]]
    plots[0]["q1"] = 9  # above the median
    bad["pt6-replay-math-m1-q14"] = box.model_copy(update={"figure": {**box.figure, "plots": plots}})
    found = {(i, p.split()[0]) for _, i, p in check_pt6(bad)}
    assert ("pt6-replay-rw-m2-q12", "key") in found
    assert ("pt6-replay-rw-m2-q16", "trap") in found
    assert ("pt6-replay-rw-m1-q14", "repeats") in found
    assert ("pt6-replay-math-m1-q14", "box") in found
    del bad["pt6-replay-math-m2-q22"]
    assert ("pt6", "pt6-replay-math-m2-q22", "missing replay twin") in check_pt6(bad)


def test_spr_grader_accepts_every_listed_entry() -> None:
    for i in items().values():
        if isinstance(i, MathItem) and i.format == "spr":
            keys = [Fraction(a) for a in i.spr_answers or []]
            assert all(is_correct(e, keys) for e in i.spr_entries or []), i.id
            assert not any(is_correct(t, keys) for t in i.spr_traps or {}), i.id
    assert is_correct("3.333", [Fraction(10, 3)]) and not is_correct("3.33", [Fraction(10, 3)])


async def test_twins_plus_practice_and_timed_modes(user: AsyncClient) -> None:
    twins = (await user.get("/api/pt6/replay?kind=twins")).json()
    assert len(twins) == 70
    assert [q["label"] for q in twins[:2]] == [f"{label(SOURCE[0])} · Twin 2", f"{label(SOURCE[0])} · Twin 3"]
    speed = (await user.get("/api/pt6/replay?kind=speed")).json()
    assert [q["label"].split(" · ")[2] for q in speed] == ["Q17", "Q19", "Q21", "Q22"]
    for mode, n, limit in (("twin2rw", 25, 30 * 60), ("twin3rw", 25, 32 * 60), ("twinsmath", 20, 32 * 60)):
        body = (await user.post("/api/triage/start", json={"mode": mode})).json()
        assert len(body["questions"]) == n and body["limit_seconds"] == limit, mode


def test_twin_rules() -> None:
    good = items()
    bad = dict(good)
    t2 = good["pt6-twin2-rw-m2-q12"]
    bad["pt6-twin2-rw-m2-q12"] = t2.model_copy(update={"answer": "D"})  # the record's letter
    t3 = good["pt6-twin3-rw-m1-q01"]
    assert isinstance(t3, RWSeedItem)
    bad["pt6-twin3-rw-m1-q01"] = t3.model_copy(update={"passage": " ".join(t3.passage.split()[:30])})
    del bad["pt6-speed-math-m2-q17"]
    found = {(i, p.split()[0]) for _, i, p in check_pt6(bad)}
    assert ("pt6-twin2-rw-m2-q12", "twin") in found  # "twin 2 must move the key off D"
    assert ("pt6-twin3-rw-m1-q01", "twin") in found  # "twin 3 is N words, not longer..."
    assert ("pt6-speed-math-m2-q17", "missing") in found
