import random
from collections import Counter

from app.engine import exam as bp
from app.engine import irt
from app.engine.weakness import Attempt, weakness
from app.services.questions import load_taxonomy

LEAVES = {
    sec: [(n["id"], n["weight"]) for n in load_taxonomy() if n["level"] == "subskill" and n["section"] == sec]
    for sec in ("RW", "MATH")
}


def test_ability_is_monotone_and_prior_shrinks() -> None:
    assert irt.ability([]) == 0
    few = irt.ability([(0.0, True, 1.0)] * 2)
    many = irt.ability([(0.0, True, 1.0)] * 20)
    assert 0 < few < many <= 4
    assert irt.ability([(1.0, True, 1.0), (1.0, False, 1.0)]) > irt.ability(
        [(-1.0, True, 1.0), (-1.0, False, 1.0)]
    )  # same raw score on harder items is worth more


def test_routing_and_section_score() -> None:
    strong = [(b, True) for b in (-1.0, 0.0, 1.0) * 6] + [(1.0, False)] * 2
    weak = [(b, b < 0) for b in (-1.0, 0.0, 1.0) * 7]
    assert irt.route(strong) == "harder" and irt.route(weak) == "easier"
    perfect = [(1.0, True)] * 44
    assert irt.section_score(perfect, "harder") >= 750
    assert irt.section_score(perfect, "easier") == irt.EASIER_ROUTE_CAP
    assert irt.section_score([(-1.0, False)] * 44, "easier") == 200
    assert irt.section_score(weak, "easier") % 10 == 0


def test_target_difficulty_aims_for_two_thirds_success() -> None:
    assert irt.target_difficulty(-2.0) == "easy"
    assert irt.target_difficulty(0.6) == "medium"
    assert irt.target_difficulty(2.0) == "hard"


def test_weakness_ranks_misses_and_slowness_above_unseen_above_mastered() -> None:
    def w(attempts: list[Attempt], section: str = "RW") -> float:
        return weakness("X", section, 0.03, 0.03, attempts).score

    miss = Attempt(correct=False, b=0.0, time_ms=60_000, age_days=0, exam=True)
    hit = Attempt(correct=True, b=0.0, time_ms=60_000, age_days=0, exam=True)
    slow_hit = Attempt(correct=True, b=0.0, time_ms=200_000, age_days=0, exam=True)
    assert w([miss, miss]) > w([]) > w([hit, hit, hit])
    assert w([slow_hit] * 3) > w([hit] * 3)
    assert w([miss], "MATH") > w([miss], "RW")  # Math boost
    stale = Attempt(correct=True, b=0.0, time_ms=60_000, age_days=40, exam=False)
    assert w([stale] * 3) > w([hit] * 3)
    r = weakness("X", "RW", 0.03, 0.03, [miss, slow_hit]).reasons
    assert "Missed 1 of the last 2" in r and any("slower" in s for s in r)
    assert weakness("X", "MATH", 0.03, 0.03, []).reasons == ["Not tried yet"]


def test_quotas_sum_exactly() -> None:
    for shares in bp.PROFILES["official"].values():
        for n in (22, 27):
            q = bp.quotas(shares, n)
            assert sum(q) == n and all(c >= 0 for c in q)


def test_slots_follow_blueprint_and_profile() -> None:
    rng = random.Random(1)
    for section, (operational, _) in bp.MODULE_SPEC.items():
        s = bp.slots(section, "brutal", "harder", LEAVES[section], rng)
        assert len(s) == operational + bp.PRETEST_PER_MODULE
        assert sum(x.pretest for x in s) == bp.PRETEST_PER_MODULE
        domains = Counter(x.domain for x in s if not x.pretest)
        assert domains == Counter(bp.BLUEPRINT[section])
        assert all(bp.domain_of(x.leaf) == x.domain for x in s)
        diffs = Counter(x.difficulty for x in s)
        assert diffs["easy"] == 0 and diffs["hard"] > diffs["medium"]


def test_official_ordering() -> None:
    rng = random.Random(2)
    rw = [
        ("RW.SEC.BND.X", 1.0),
        ("RW.EOI.TRN.X", -1.0),
        ("RW.CAS.WIC.X", 1.0),
        ("RW.SEC.FSS.X", -1.0),
        ("RW.CAS.WIC.Y", -1.0),
        ("RW.INI.CID.X", 0.0),
        ("RW.CAS.CTC.X", 0.0),
    ]
    got = [rw[i] for i in bp.order("RW", rw, rng)]
    assert got == [
        ("RW.CAS.CTC.X", 0.0),
        ("RW.CAS.WIC.Y", -1.0),
        ("RW.CAS.WIC.X", 1.0),
        ("RW.INI.CID.X", 0.0),
        ("RW.SEC.FSS.X", -1.0),  # SEC: easy→hard regardless of skill
        ("RW.SEC.BND.X", 1.0),
        ("RW.EOI.TRN.X", -1.0),
    ]
    math = [("MATH.GEO.CIR.A", 1.0), ("MATH.ALG.LIN1.A", 0.0), ("MATH.PSD.PCT.A", -1.0)]
    assert [math[i][1] for i in bp.order("MATH", math, rng)] == [-1.0, 0.0, 1.0]
