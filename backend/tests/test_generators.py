import json
import os
import random
from fractions import Fraction
from pathlib import Path

import pytest
import sympy

from app.generators import DIFFICULTIES, REGISTRY, generate
from app.generators.core import ERROR_MODELS
from app.generators.spr import canonical_entry, is_correct, is_valid_entry

SEEDS = int(os.environ.get("GEN_SEEDS", "200"))
TAXONOMY = json.loads((Path(__file__).parents[1] / "app/seed/taxonomy.json").read_text())
MATH_LEAVES = sorted(
    n["id"] for n in TAXONOMY["nodes"] if n["level"] == "subskill" and n["section"] == "MATH"
)


def test_every_math_subskill_has_a_generator() -> None:
    assert sorted(REGISTRY) == MATH_LEAVES


def _num(v: object) -> sympy.Basic | None:
    if isinstance(v, str):
        return None
    e = sympy.sympify(v)
    return e if e.is_number else None


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
@pytest.mark.parametrize("skill", sorted(REGISTRY))
def test_generator(skill: str, difficulty: str) -> None:
    formats = set()
    for seed in range(SEEDS):
        g = generate(skill, difficulty, random.Random(seed))  # type: ignore[arg-type]
        ctx = f"{skill}/{difficulty}/seed={seed}"
        assert g.verify(), ctx
        assert g.stem and g.explanation, ctx
        formats.add(g.format)
        if g.format == "mc":
            assert g.choices and len(g.choices) == 4 and len(set(g.choices)) == 4, ctx
            assert g.answer in "ABCD", ctx
            assert set(g.error_models) == set("ABCD") - {g.answer}, ctx
            assert all(mo in ERROR_MODELS for mo in g.error_models.values()), ctx
            key_n = _num(g.key_value)
            for dv in g.distractor_values:
                dn = _num(dv)
                if key_n is not None and dn is not None:
                    assert abs(complex(sympy.N(dn - key_n, 20))) > 1e-9, ctx
                elif isinstance(dv, str) and isinstance(g.key_value, str):
                    assert dv != g.key_value, ctx
        else:
            assert g.spr_answers, ctx
            entry = canonical_entry(g.spr_answers[0])
            assert is_valid_entry(entry) and is_correct(entry, g.spr_answers), (ctx, entry)
        # fixed-seed reproducibility
        assert generate(skill, difficulty, random.Random(seed)).content() == g.content(), ctx
    assert "mc" in formats, skill


def test_spr_official_examples() -> None:
    two_thirds, neg_third = [Fraction(2, 3)], [Fraction(-1, 3)]
    for ok in ["2/3", ".6666", ".6667", "0.666", "0.667", "4/6"]:
        assert is_correct(ok, two_thirds), ok
    for bad in ["0.66", ".66", "0.67", ".67", "0.6667", "3 1/2", "2/0", "2//3", "--2"]:
        assert not is_correct(bad, two_thirds), bad
    for ok in ["-1/3", "-.3333", "-0.333"]:
        assert is_correct(ok, neg_third), ok
    assert not is_correct("-.33", neg_third)
    assert is_correct("7/2", [Fraction(7, 2)]) and is_correct("3.5", [Fraction(7, 2)])
    assert not is_correct("3 1/2", [Fraction(7, 2)])
    assert not is_correct("$5", [Fraction(5)]) and not is_correct("1,000", [Fraction(1000)])
    assert not is_correct("123456", [Fraction(123456)])  # too long
    assert canonical_entry(Fraction(2, 3)) == "2/3" and canonical_entry(Fraction(-1, 3)) == "-1/3"
    assert canonical_entry(Fraction(1234, 777)) == "1.588"
    assert canonical_entry(Fraction(-9876, 70)) == "-141.1"
