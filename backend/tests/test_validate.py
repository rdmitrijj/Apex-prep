import json
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from sympy import sympify

from app import validate
from app.generators.spr import is_correct
from app.schemas.question import MathItem, RWItem, RWSeedItem
from app.validate import check_bank, check_math, check_rw, same

LEAVES = {"MATH.ADV.NLF.POLYZ", "MATH.ALG.LIN2.SOLN", "RW.CAS.WIC.FILL"}
WHY = "Sign error: this one is wrong."


def zeros_item(**kw: Any) -> MathItem:
    base: dict[str, Any] = {
        "id": "m-test-zeros",
        "skill": "MATH.ADV.NLF.POLYZ",
        "difficulty": "easy",
        "format": "mc",
        "stem": "The function $f$ is defined by $f(x) = (x+8)(x+2)(x-8)$. "
        "Which of the following is a zero of $f$?",
        "choices": ["$-2$", "$2$", "$8$", "$16$"],
        "values": ["-2", "2", "8", "16"],
        "answer": "A",
        "rationales": {"A": "Correct. x + 2 = 0 at x = -2.", "B": WHY, "C": WHY, "D": WHY},
        "check": "-2",
        "accepts": "(v+8)*(v+2)*(v-8)",
        "explanation": ["A product is zero when a factor is zero."],
    }
    return MathItem.model_validate(base | kw)


def test_double_correct_zero_is_caught() -> None:
    errs = check_math(zeros_item(), LEAVES)
    assert any("C = 8 is ALSO correct" in e for e in errs), errs
    ok = zeros_item(choices=["$-2$", "$2$", "$-16$", "$16$"], values=["-2", "2", "-16", "16"])
    assert check_math(ok, LEAVES) == []


def test_multi_answer_stem_needs_a_predicate() -> None:
    errs = check_math(zeros_item(accepts=None, values=["-2", "2", "-16", "16"]), LEAVES)
    assert any("accepts" in e for e in errs), errs


def test_wrong_key_and_equivalent_forms() -> None:
    item = zeros_item(
        stem="What is the value of $x$ if $2x = 4$?",
        accepts=None,
        check="solve(2*x - 4, x)[0]",
        values=["4/2", "1", "4", "-2"],
    )
    assert check_math(item, LEAVES) == []
    errs = check_math(item.model_copy(update={"answer": "B"}), LEAVES)
    assert "key B = 1 is not correct (check gives 2)" in errs and "distractor A = 2 is ALSO correct" in errs
    assert same(sympify("x >= 6*n - 12"), sympify("6*n - 12 <= x"))
    assert not same(sympify("x >= 6*n - 12"), sympify("x <= 6*n - 12"))
    assert same(sympify("Eq(8*x + 12*y, 480)"), sympify("Eq(2*x + 3*y, 120)"))
    assert same(sympify("(1, -2)"), sympify("(1, -2)")) and not same(sympify("(1, -2)"), sympify("(-2, 1)"))


def test_spr_item_entries() -> None:
    item = MathItem.model_validate(
        {
            "id": "m-test-spr",
            "skill": "MATH.ALG.LIN2.SOLN",
            "difficulty": "hard",
            "format": "spr",
            "stem": "The line $9x - 10y = 19$ is shifted down 4 units. What is the new $x$-intercept?",
            "check": "solve(9*x - 10*(0 + 4) - 19, x)[0]",
            "spr_answers": ["59/9"],
            "spr_entries": ["59/9", "6.555", "6.556", "6.55"],
            "explanation": ["Replace y with y + 4."],
        }
    )
    assert check_math(item, LEAVES) == ["sample entry '6.55' is graded wrong"]


def test_spr_grader_accepts_every_valid_form() -> None:
    k = [Fraction(59, 9)]
    for ok in ["59/9", "6.555", "6.556"]:
        assert is_correct(ok, k), ok
    for bad in ["6.55", "6.5", "6 5/9", "6.5555"]:
        assert not is_correct(bad, k), bad
    neg = [Fraction(-14, 15)]
    for ok in ["-14/15", "-.9333", "-0.933", "-28/30"]:
        assert is_correct(ok, neg), ok
    for bad in ["-.93", "-0.93", "14/15"]:
        assert not is_correct(bad, neg), bad
    assert not is_correct("3 1/2", [Fraction(7, 2)]) and is_correct("7/2", [Fraction(7, 2)])


def test_rw_checks() -> None:
    item = RWItem.model_validate(
        {
            "id": "rw-test-001",
            "skill": "RW.CAS.WIC.FILL",
            "difficulty": "easy",
            "passage": "Critics doubted the plan, but their concerns didn't ______ it; the hinder was minor.",
            "stem": "Which choice completes the text with the most logical and precise word or phrase?",
            "choices": ["hinder", "praise", "reveal", "copy"],
            "answer": "A",
            "explanation": "The concerns did not hold the plan back.",
            "rationales": {"A": "Correct. Fits.", "B": "Opposite.", "C": "Off topic.", "D": "Off topic."},
        }
    )
    errs = check_rw(item, LEAVES)
    assert any("13 words" in e for e in errs) and any("appears in the passage" in e for e in errs), errs


def rw_item(**kw: Any) -> RWSeedItem:
    base: dict[str, Any] = {
        "id": "rw-tri-test-001",
        "skill": "RW.CAS.WIC.FILL",
        "difficulty": "hard",
        "topic": "test",
        "fictional": True,
        "passage": "The committee praised the plan's ambition but ______ its approval, attaching conditions "
        "that an independent audit would have to confirm before any money could be spent on it.",
        "stem": "Which choice completes the text with the most logical and precise word or phrase?",
        "choices": ["qualified", "hastened", "disguised", "multiplied"],
        "answer": "A",
        "explanation": "Approval with conditions is limited approval.",
        "steps": ["One.", "Two.", "Three."],
        "strategy_tip": "Predict a word first.",
        "rationales": {"A": "Correct. Limited.", "B": WHY, "C": WHY, "D": WHY},
        "traps": {"B": "wrong logic", "C": "wrong logic", "D": "wrong logic"},
        "vocab": [
            {
                "word": w,
                "pos": "verb",
                "meaning_en": "a meaning",
                "meaning_ru": "значение",
                "example": "An example sentence.",
            }
            for w in ("qualified", "hastened", "disguised", "multiplied")
        ],
    }
    return RWSeedItem.model_validate(base | kw)


def test_study_fields() -> None:
    assert check_rw(rw_item(), LEAVES) == []
    vocab = rw_item().vocab or []
    mixed = [v.model_copy(update={"pos": "adjective"}) if v.word == "hastened" else v for v in vocab]
    assert "choices are not all the same part of speech" in check_rw(rw_item(vocab=mixed), LEAVES)
    assert any("without a vocab entry" in e for e in check_rw(rw_item(vocab=vocab[:3]), LEAVES))
    assert any("traps must name" in e for e in check_rw(rw_item(traps={"A": "x"}), LEAVES))
    bnd = rw_item(skill="RW.SEC.BND.SUPP", vocab=None, choices=["zero—", "zero,", "zero;", "many zeros"])
    assert "boundaries choices differ in more than punctuation" in check_rw(bnd, LEAVES | {"RW.SEC.BND.SUPP"})


def test_quant_numbers_must_come_from_the_figure() -> None:
    fig = {
        "kind": "table",
        "header": ["Branch", "Before", "After"],
        "rows": [["North", "410", "520"], ["South", "300", "310"]],
    }
    roles = {"A": "supports", "B": "true_but_irrelevant", "C": "false", "D": "misread"}
    item = rw_item(
        skill="RW.INI.COEQ.TABLE",
        vocab=None,
        figure=fig,
        quant=roles,
        choices=[
            "North rose by 110, more than South's 10.",
            "South had 300 before.",
            "South rose by 99.",
            "North fell.",
        ],
    )
    assert check_rw(item, LEAVES | {"RW.INI.COEQ.TABLE"}) == []
    bad = item.model_copy(update={"choices": ["North rose by 111.", *item.choices[1:]]})
    assert any("cites ['111']" in e for e in check_rw(bad, LEAVES | {"RW.INI.COEQ.TABLE"}))
    two = item.model_copy(update={"quant": {**roles, "B": "supports"}})
    assert any("exactly one choice" in e for e in check_rw(two, LEAVES | {"RW.INI.COEQ.TABLE"}))


def test_bank_balance_length_and_blind(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    key = {"answer": "D", "rationales": {"A": WHY, "B": WHY, "C": WHY, "D": "Correct. Longest."}}
    items = [rw_item(id=f"rw-tri-test-{n:03}", **key) for n in range(8)]
    items = [i.model_copy(update={"passage": f"{i.passage} {n}"}) for n, i in enumerate(items)]
    blind = tmp_path / "blind.json"
    blind.write_text(json.dumps({i.id: "multiplied" for i in items}))
    monkeypatch.setattr(validate, "BLIND", blind)
    errs = [p for _, _, p in check_bank(items)]
    assert any("unbalanced key" in e for e in errs), errs  # every key is D
    assert any("key is the longest choice in 8/8" in e for e in errs), errs
    assert any("similar to" in e for e in errs), errs
    blind.write_text(json.dumps({items[0].id: "hastened"}))  # the solver disagreed with the key
    errs = [p for _, _, p in check_bank(items[:1])]
    assert any("blind re-solve picked 'hastened'" in e for e in errs), errs
