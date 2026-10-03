"""Problem-Solving and Data Analysis generators (MATH.PSD.*)."""

import random
import statistics
from typing import Any

import sympy

from app.generators.core import (
    D,
    Difficulty,
    Generated,
    R,
    build,
    dec_fmt,
    ds,
    holds,
    m,
    num,
    register,
    ri,
    tex,
    x,
)

S = "MATH.PSD."


def _pct(v: sympy.Basic) -> str:
    return f"${num(v)}\\%$"


# ---------- RAT: ratios, rates, units ----------


@register(S + "RAT.PROP")
def rat_prop(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "RAT.PROP"
    if d == "easy":
        a, b = ri(rng, 2, 6), ri(rng, 12, 36)
        c = b * ri(rng, 2, 4) + rng.choice([0, b // 2 if b % 2 == 0 else 0])
        key = sympy.solve(sympy.Eq(R(a, b), x / c), x)[0]
        stem = f"A recipe uses {a} cups of flour to make {b} muffins. At this rate, how many cups of flour are needed to make {c} muffins?"
        dist = ds(
            (lambda: R(b * c, a), "reciprocal", "Set up the proportion upside down (muffins per cup)."),
            (lambda: R(a + c - b), "wrong_formula", "Added the difference instead of scaling by a ratio."),
            (lambda: R(a * c), "partial_solution", f"Forgot to divide by {b}."),
            (lambda: R(c, b), "partial_solution", f"That's the scale factor; multiply by {a}."),
        )
        steps = [f"$\\frac{{{a}}}{{{b}}} = \\frac{{x}}{{{c}}}$", f"$x = {tex(key)}$ cups."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: holds(key * b, a * c, {}),
        )
    if d == "medium":
        p_, q_ = rng.sample(range(1, 10), 2)
        while sympy.gcd(p_, q_) != 1:
            p_, q_ = rng.sample(range(1, 10), 2)
        n = (p_ + q_) * ri(rng, 3, 12)
        key = sympy.solve(sympy.Eq(x + x * R(q_, p_), n), x)[0]
        stem = f"A bag contains only red and blue marbles in the ratio {p_} to {q_}. If the bag has {n} marbles, how many are red?"
        dist = ds(
            (lambda: R(n * q_, p_ + q_), "misread", "That's the number of blue marbles."),
            (
                lambda: R(n * p_, q_),
                "wrong_formula",
                "Used the part-to-part ratio as if it were part-to-whole.",
            ),
            (lambda: R(n, p_ + q_), "partial_solution", "That's one 'share'; multiply by the red part."),
            (lambda: R(n, 2), "concept", "The ratio isn't 1 to 1."),
        )
        steps = [
            f"Red is $\\frac{{{p_}}}{{{p_ + q_}}}$ of the total.",
            f"$\\frac{{{p_}}}{{{p_ + q_}}} \\times {n} = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: holds(key / (n - key), R(p_, q_), {}),
        )
    p_, q_, r_, s_ = (ri(rng, 1, 9) for _ in range(4))
    nc = q_ * s_ * ri(rng, 1, 6)
    a_, b_ = sympy.symbols("a b")
    sol = sympy.solve([sympy.Eq(a_ * q_, b_ * p_), sympy.Eq(b_ * s_, nc * r_)], [a_, b_])
    key = sol[a_]
    stem = (
        f"In a garden, the ratio of tulips to roses is {p_} to {q_}, and the ratio of roses to lilies is {r_} to {s_}. "
        f"If there are {nc} lilies, how many tulips are there?"
    )
    dist = ds(
        (lambda: R(nc * p_ * s_, q_ * r_), "reciprocal", "Inverted the roses-to-lilies ratio."),
        (lambda: sol[b_], "partial_solution", "That's the number of roses."),
        (lambda: R(nc * p_, s_), "wrong_formula", "Chained the ratios without matching the roses term."),
        (lambda: R(nc * p_, q_), "misread", "Treated lilies as roses."),
    )
    steps = [
        f"Roses: $\\frac{{{r_}}}{{{s_}}} \\times {nc} = {tex(sol[b_])}$.",
        f"Tulips: $\\frac{{{p_}}}{{{q_}}} \\times {tex(sol[b_])} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=dec_fmt,
        verify=lambda: holds(key, R(p_ * r_ * nc, q_ * s_), {}),
    )


@register(S + "RAT.UNITS")
def rat_units(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "RAT.UNITS"
    if d == "easy":
        v = ri(rng, 2, 30) * 5
        key = R(v) * 3600 / 1000
        stem = f"A train travels at {v} meters per second. What is this speed in kilometers per hour?"
        dist = ds(
            (lambda: R(v) * 1000 / 3600, "operation_swap", "Converted in the wrong direction."),
            (lambda: R(v * 60, 1000), "partial_solution", "Converted seconds to minutes, not hours."),
            (lambda: R(v * 3600), "unit_slip", "Converted to meters per hour, not kilometers."),
            (lambda: R(v * 60), "unit_slip", "Multiplied by 60 once and stopped."),
        )
        steps = [
            f"${v}\\ \\frac{{\\text{{m}}}}{{\\text{{s}}}} \\times \\frac{{3600\\ \\text{{s}}}}{{1\\ \\text{{h}}}} \\times \\frac{{1\\ \\text{{km}}}}{{1000\\ \\text{{m}}}} = {tex(key)}$ km/h."
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: key * 1000 == v * 3600,
        )
    if d == "medium":
        p_ = ri(rng, 12, 40)
        n = p_ * 60 * ri(rng, 1, 5) // rng.choice([1, 2, 4])
        key = R(n, 60 * p_)
        stem = f"A printer prints {p_} pages per minute. How many hours will it take to print {n} pages?"
        dist = ds(
            (lambda: R(n, p_), "unit_slip", "That's the time in minutes."),
            (lambda: R(n * 60, p_), "operation_swap", "Multiplied by 60 instead of dividing."),
            (lambda: R(n * p_, 60), "operation_swap", "Multiplied by the rate instead of dividing."),
            (lambda: R(60 * p_, n), "reciprocal", "Inverted the ratio."),
        )
        steps = [
            f"Minutes: ${n} \\div {p_} = {tex(R(n, p_))}$.",
            f"Hours: ${tex(R(n, p_))} \\div 60 = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: key * 60 * p_ == n,
        )
    a, b = 3 * ri(rng, 3, 8), 3 * ri(rng, 3, 8)
    c = ri(rng, 12, 45)
    key = R(a * b, 9) * c
    stem = f"A rectangular floor measures {a} feet by {b} feet. Carpet costs \\${c} per square yard. What is the cost, in dollars, to carpet the floor? (1 yard = 3 feet)"
    dist = ds(
        (lambda: R(a * b, 3) * c, "unit_slip", "One square yard is $3 \\times 3 = 9$ square feet, not 3."),
        (lambda: R(a * b * c), "unit_slip", "Priced square feet as if they were square yards."),
        (lambda: R(a * b, 9), "partial_solution", "That's the area in square yards."),
        (lambda: R(2 * (a + b), 3) * c, "wrong_formula", "Used the perimeter instead of the area."),
    )
    steps = [
        f"Area: ${a} \\times {b} = {a * b}$ ft² $= {tex(R(a * b, 9))}$ yd².",
        f"Cost: ${tex(R(a * b, 9))} \\times {c} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=dec_fmt,
        verify=lambda: key == R(a, 3) * R(b, 3) * c,
    )


# ---------- PCT: percentages ----------


@register(S + "PCT.BASIC")
def pct_basic(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "PCT.BASIC"
    if d == "easy":
        p_, n = rng.choice([5, 10, 15, 20, 25, 30, 40, 45, 60, 75]), ri(rng, 2, 40) * 20
        key = R(p_, 100) * n
        stem = f"What is {p_}% of {n}?"
        dist = ds(
            (lambda: R(n * p_), "unit_slip", "Forgot to divide by 100."),
            (lambda: n + key, "misread", f"That's {n} increased by {p_}%."),
            (lambda: n - key, "misread", f"That's {n} decreased by {p_}%."),
            (lambda: R(n, p_), "operation_swap", "Divided by the percent instead of multiplying."),
        )
        steps = [f"${p_ / 100:g} \\times {n} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: key * 100 == p_ * n,
        )
    if d == "medium":
        a = ri(rng, 4, 40) * 5
        up = rng.choice([True, False])
        pc = rng.choice([4, 5, 8, 10, 12, 15, 20, 25, 30, 40, 60])
        b = a + a * pc // 100 * (1 if up else -1)
        while (a * pc) % 100:
            a += 5
            b = a + a * pc // 100 * (1 if up else -1)
        key = abs(R(b - a, a)) * 100
        word = "increase" if up else "decrease"
        stem = f"The price of a jacket changed from \\${a} to \\${b}. What was the percent {word}?"
        dist = ds(
            (
                lambda: abs(R(b - a, b)) * 100,
                "wrong_formula",
                "Divided by the new price; percent change uses the original.",
            ),
            (lambda: R(abs(b - a)), "partial_solution", "That's the change in dollars."),
            (lambda: R(b, a) * 100, "concept", "That's the new price as a percent of the original."),
            (
                lambda: R(100) - key if up else R(100) + key,
                "concept",
                "Mixed up the change and what remains.",
            ),
        )
        steps = [f"Change: ${abs(b - a)}$.", f"$\\frac{{{abs(b - a)}}}{{{a}}} \\times 100 = {tex(key)}\\%$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(a * (1 + (1 if up else -1) * key / 100), b, {}),
            fmt=_pct_fmt,
        )
    p_, q_ = rng.choice([20, 25, 40, 50, 60, 75, 80, 120, 150]), rng.choice([10, 20, 25, 30, 40, 50, 80, 125])
    key = R(p_ * q_, 100)
    stem = f"The number $a$ is {p_}% of $b$, and $b$ is {q_}% of $c$. The number $a$ is what percent of $c$?"
    dist = ds(
        (lambda: R(p_ + q_), "wrong_formula", "Percents of percents multiply; they don't add."),
        (lambda: R(p_ * q_), "unit_slip", "Multiplied the percents without converting to decimals."),
        (lambda: R(p_ + q_, 2), "concept", "Averaged the percents."),
        (lambda: R(p_ * 100, q_), "operation_swap", "Divided instead of multiplying."),
    )
    steps = [
        f"$a = {p_ / 100:g}b$ and $b = {q_ / 100:g}c$.",
        f"$a = {p_ / 100:g} \\times {q_ / 100:g}c = {tex(key / 100)}c$, i.e. ${tex(key)}\\%$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(R(p_, 100) * R(q_, 100) * 1000, key * 10, {}),
        fmt=_pct_fmt,
    )


def _pct_fmt(v: Any) -> str:
    return v if isinstance(v, str) else _pct(v)


@register(S + "PCT.SUCC")
def pct_succ(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "PCT.SUCC"
    if d == "easy":
        p_ = rng.choice([10, 20, 25, 30, 40, 50])
        price = ri(rng, 2, 20) * 100
        r = R(p_, 100)
        key = price * (1 + r) * (1 - r)
        stem = f"A store raised the price of a \\${price} bicycle by {p_}%. Later, it lowered the new price by {p_}%. What is the final price, in dollars?"
        dist = ds(
            (
                lambda: R(price),
                "concept",
                "A percent decrease is taken of the larger, raised price, so the changes don't cancel.",
            ),
            (lambda: price * (1 + r), "partial_solution", "That's the price after the increase only."),
            (
                lambda: price * (1 + r) - price * r * (1 - r),
                "wrong_formula",
                "Took the decrease from the wrong base.",
            ),
            (lambda: price * (1 - r) ** 2, "sign_flip", "Applied two decreases."),
        )
        steps = [
            f"After the increase: ${price} \\times {1 + p_ / 100:g} = {tex(price * (1 + r))}$.",
            f"After the decrease: $\\times {1 - p_ / 100:g} = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: holds(key, price * (1 - r**2), {}),
        )
    if d == "medium":
        p_ = rng.choice([10, 15, 20, 25, 30, 40, 60])
        orig = ri(rng, 2, 30) * 20
        r = R(p_, 100)
        final = orig * (1 - r)
        key = sympy.solve(sympy.Eq(x * (1 - r), final), x)[0]
        stem = (
            f"After a {p_}% discount, a coat costs \\${num(final)}. What was the original price, in dollars?"
        )
        dist = ds(
            (
                lambda: final * (1 + r),
                "concept",
                f"The {p_}% was taken of the original price, not the sale price.",
            ),
            (lambda: final * (1 - r), "sign_flip", "Applied the discount again."),
            (lambda: final + p_, "unit_slip", f"Added {p_} dollars instead of {p_} percent."),
            (lambda: final / r, "wrong_formula", "Divided by the discount rate instead of by what remains."),
        )
        steps = [
            f"Sale price $= (1 - {p_ / 100:g}) \\times$ original.",
            f"Original $= {tex(final)} \\div {1 - p_ / 100:g} = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: key == orig,
        )
    p_, q_ = rng.choice([10, 20, 25, 50]), rng.choice([10, 20, 25, 40])
    orig = ri(rng, 2, 20) * 100
    final = orig * (1 + R(p_, 100)) * (1 - R(q_, 100))
    key = sympy.solve(sympy.Eq(x * (1 + R(p_, 100)) * (1 - R(q_, 100)), final), x)[0]
    stem = f"The value of a stock increased by {p_}% in January and then decreased by {q_}% in February, ending at \\${num(final)}. What was its value, in dollars, at the start of January?"
    dist = ds(
        (
            lambda: final / (1 + R(p_ - q_, 100)),
            "wrong_formula",
            "Combined the percents by adding; successive changes multiply.",
        ),
        (
            lambda: final * (1 - R(p_, 100)) * (1 + R(q_, 100)),
            "concept",
            "Undoing a percent change means dividing, not applying the opposite percent.",
        ),
        (lambda: final / (1 + R(p_, 100)), "partial_solution", "Undid only the January change."),
        (lambda: final / (1 - R(q_, 100)), "partial_solution", "Undid only the February change."),
    )
    steps = [
        f"Final $=$ start $\\times {1 + p_ / 100:g} \\times {1 - q_ / 100:g}$.",
        f"Start $= {tex(final)} \\div {tex((1 + R(p_, 100)) * (1 - R(q_, 100)))} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=dec_fmt,
        verify=lambda: key == orig,
    )


# ---------- ONEVAR: one-variable data ----------


def _mean(v: list[int]) -> sympy.Rational:
    return R(sum(v), len(v))


def _median(v: list[int]) -> sympy.Rational:
    s = sorted(v)
    n = len(s)
    return R(s[n // 2]) if n % 2 else R(s[n // 2 - 1] + s[n // 2], 2)


@register(S + "ONEVAR.CENTER")
def onevar_center(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "ONEVAR.CENTER"
    if d == "easy":
        vals = [ri(rng, 2, 30) for _ in range(rng.choice([5, 6, 7]))]
        key = _mean(vals)
        stem = f"The data set lists the number of books read by students in a club: {', '.join(map(str, vals))}. What is the mean of the data set?"
        dist = ds(
            (lambda: _median(vals), "misread", "That's the median."),
            (lambda: R(sum(vals)), "partial_solution", "That's the sum; divide by the count."),
            (
                lambda: R(sum(vals), len(vals) - 1),
                "off_by_one",
                "Divided by one less than the number of values.",
            ),
            (lambda: R(max(vals) + min(vals), 2), "concept", "That's the midrange, not the mean."),
        )
        steps = [f"Sum $= {sum(vals)}$, count $= {len(vals)}$.", f"Mean $= {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: holds(key, R(statistics.fmean(vals)).limit_denominator(1000), {}),
        )
    if d == "medium":
        n, m1 = ri(rng, 4, 12), ri(rng, 60, 90)
        new = ri(rng, 40, 100)
        while new == m1:
            new = ri(rng, 40, 100)
        m2 = R(n * m1 + new, n + 1)
        key = sympy.solve(sympy.Eq((n * m1 + x) / (n + 1), m2), x)[0]
        stem = f"The mean score of {n} students on a quiz was {m1}. After one more student took the quiz, the mean score of all {n + 1} students was ${num(m2)}$. What was the score of the last student?"
        dist = ds(
            (lambda: m2, "misread", "That's the new mean."),
            (lambda: n * m2 - n * m1, "off_by_one", f"Used {n} instead of {n + 1} for the new total."),
            (lambda: 2 * m2 - m1, "wrong_formula", "Averaged the two means as if each counted once."),
            (lambda: R(n + 1) * m2, "partial_solution", "That's the new total of all scores."),
        )
        steps = [
            f"New total: ${n + 1} \\times {tex(m2)} = {tex((n + 1) * m2)}$.",
            f"Old total: ${n} \\times {m1} = {n * m1}$.",
            f"Last score: ${tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: key == new,
        )
    vals = sorted(ri(rng, 10, 30) for _ in range(rng.choice([6, 7, 8])))
    vals[-1] = ri(rng, 80, 150)
    rest = vals[:-1]
    key = _mean(vals) - _mean(rest)
    stem = f"A data set consists of the values {', '.join(map(str, vals))}. If the value {vals[-1]} is removed, by how much does the mean decrease?"
    dist = ds(
        (lambda: _median(vals) - _median(rest), "concept", "That's the change in the median."),
        (lambda: R(vals[-1], len(vals)), "wrong_formula", "Removing a value also changes the count."),
        (lambda: _mean(rest), "misread", "That's the new mean."),
        (
            lambda: R(vals[-1]) - _mean(rest),
            "wrong_formula",
            "That's how far the removed value was from the new mean.",
        ),
    )
    steps = [
        f"Mean with it: ${tex(_mean(vals))}$; without it: ${tex(_mean(rest))}$.",
        f"Decrease: ${tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=dec_fmt,
        verify=lambda: holds(key, (vals[-1] - _mean(rest)) / len(vals), {}),
    )


@register(S + "ONEVAR.SPREAD")
def onevar_spread(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "ONEVAR.SPREAD"
    if d == "easy":
        vals = [ri(rng, 1, 60) for _ in range(rng.choice([6, 7, 8]))]
        key = R(max(vals) - min(vals))
        stem = f"What is the range of the data set {', '.join(map(str, vals))}?"
        dist = ds(
            (lambda: R(max(vals)), "partial_solution", "That's the maximum; subtract the minimum."),
            (
                lambda: R(vals[-1] - vals[0]),
                "misread",
                "Subtracted the last and first listed values; order the data first.",
            ),
            (lambda: _mean(vals), "concept", "That's the mean."),
            (lambda: R(max(vals) + min(vals)), "sign_flip", "Added instead of subtracting."),
        )
        steps = [f"Max ${max(vals)}$, min ${min(vals)}$: range ${tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: key == sorted(vals)[-1] - sorted(vals)[0],
        )
    if d == "medium":
        base = [ri(rng, 10, 20) for _ in range(5)]
        while len(set(base)) < 3:
            base = [ri(rng, 10, 20) for _ in range(5)]
        case = rng.choice(["shift", "spreadA", "spreadB"])
        mu = statistics.mean(base)
        a_vals = list(base)
        b_vals = [v + 7 for v in base]
        if case == "spreadA":
            a_vals = [round(mu + 3 * (v - mu)) for v in base]
        elif case == "spreadB":
            b_vals = [round(mu + 3 * (v - mu)) + 7 for v in base]
        sa, sb = (
            sympy.sqrt(sum((R(v) - _mean(a_vals)) ** 2 for v in a_vals)),
            sympy.sqrt(sum((R(v) - _mean(b_vals)) ** 2 for v in b_vals)),
        )
        labels = {"A": "Data set A has the greater standard deviation.", "B": "Data set B has the greater standard deviation.",
                  "eq": "The standard deviations are equal.", "na": "There is not enough information to compare them."}  # fmt: skip
        found = "A" if sa > sb else "B" if sb > sa else "eq"
        key = labels[found]
        why = {"A": "Compare how spread out each set is around its own mean.", "B": "Compare how spread out each set is around its own mean.",
               "eq": "Adding the same number to every value shifts the data but doesn't change the spread; here the spreads differ.",
               "na": "Both data sets are listed, so the spreads can be compared directly."}  # fmt: skip
        if found == "eq":
            why["A"] = why["B"] = (
                "Data set B is data set A with the same number added to every value; shifting doesn't change spread."
            )
        dist = [D(v, "concept", why[c]) for c, v in labels.items() if c != found]
        stem = f"Data set A: {', '.join(map(str, a_vals))}. Data set B: {', '.join(map(str, b_vals))}. Which statement about the standard deviations of the two data sets is true?"
        steps = ["Standard deviation measures spread around the mean, not the size of the values.",
                 {"eq": "B is A shifted by 7, so the spreads are equal.", "A": "A's values are more spread out.", "B": "B's values are more spread out."}[found]]  # fmt: skip
        return build(rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps,
                     fmt=dec_fmt, verify=lambda: (statistics.pstdev(a_vals) > statistics.pstdev(b_vals) + 1e-9) == (found == "A")
                     and (abs(statistics.pstdev(a_vals) - statistics.pstdev(b_vals)) < 1e-9) == (found == "eq"))  # fmt: skip
    c, add = ri(rng, 2, 5), ri(rng, 3, 20)
    s = R(ri(rng, 2, 15), rng.choice([1, 2]))
    sample = [1, 4, 6, 9, 15]
    key = c * s
    stem = f"A data set has a standard deviation of ${tex(s)}$. Each value in the data set is multiplied by {c}, and then {add} is added to each result. What is the standard deviation of the new data set?"
    dist = ds(
        (
            lambda: c * s + add,
            "concept",
            "Adding a constant shifts every value equally; it doesn't change the spread.",
        ),
        (lambda: s, "concept", "Multiplying every value stretches the spread by that factor."),
        (
            lambda: c * c * s,
            "wrong_formula",
            f"The variance is multiplied by ${c}^2$; the standard deviation by ${c}$.",
        ),
        (lambda: s + add, "concept", "Adding doesn't change spread, but multiplying does."),
    )
    steps = [
        f"Multiplying by {c} multiplies the standard deviation by {c}; adding {add} doesn't change it.",
        f"New SD: ${tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=dec_fmt,
        verify=lambda: (
            abs(statistics.pstdev([c * v + add for v in sample]) - c * statistics.pstdev(sample)) < 1e-9
        ),
    )


@register(S + "ONEVAR.DISPLAY")
def onevar_display(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "ONEVAR.DISPLAY"
    lo = ri(rng, 0, 3)
    values = list(range(lo, lo + 5))
    counts = [ri(rng, 1, 9) for _ in values]
    data = [v for v, c in zip(values, counts, strict=True) for _ in range(c)]
    fig = {
        "kind": "bars",
        "labels": [str(v) for v in values],
        "values": counts,
        "xlabel": "Number of pets",
        "ylabel": "Number of households",
    }
    intro = "The bar graph shows the number of pets owned by each household in a survey."
    if d == "easy":
        t = values[ri(rng, 1, 3)]
        key = R(sum(1 for v in data if v > t))
        stem = f"{intro} How many households own more than {t} pets?"
        dist = ds(
            (
                lambda: R(sum(1 for v in data if v >= t)),
                "off_by_one",
                f"Included households with exactly {t} pets.",
            ),
            (
                lambda: R(sum(v for v in data if v > t)),
                "misread",
                "That's the total number of pets, not households.",
            ),
            (
                lambda: R(len([v for v in values if v > t])),
                "misread",
                "Counted bars instead of adding their heights.",
            ),
            (lambda: R(len(data)) - key, "concept", f"That's the number with at most {t} pets."),
        )
        steps = [f"Add the bars for values greater than {t}: ${tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            fmt=dec_fmt,
            verify=lambda: key == len([v for v in data if v > t]),
        )
    if d == "medium":
        key = _median(data)
        stem = f"{intro} What is the median number of pets per household?"
        dist = ds(
            (lambda: _mean(data), "concept", "That's the mean."),
            (lambda: R(values[2]), "misread", "That's the middle category, not the middle household."),
            (lambda: R(values[counts.index(max(counts))]), "concept", "That's the mode (the tallest bar)."),
            (lambda: R(sorted(counts)[2]), "misread", "That's the median of the bar heights."),
        )
        steps = [
            f"There are {len(data)} households; the median is the middle value when listed in order.",
            f"Median $= {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            fmt=dec_fmt,
            verify=lambda: holds(key, R(statistics.median(data)).limit_denominator(10), {}),
        )
    key = _mean(data)
    stem = f"{intro} What is the mean number of pets per household?"
    dist = ds(
        (lambda: _median(data), "concept", "That's the median."),
        (
            lambda: R(sum(values), len(values)),
            "concept",
            "Averaged the categories without weighting by frequency.",
        ),
        (lambda: R(sum(counts), len(values)), "misread", "Averaged the bar heights."),
        (
            lambda: R(sum(data), len(values)),
            "wrong_formula",
            "Divided the total pets by the number of categories.",
        ),
    )
    steps = [
        f"Total pets: ${' + '.join(f'{v}({c})' for v, c in zip(values, counts, strict=True))} = {sum(data)}$.",
        f"Households: ${len(data)}$. Mean $= {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        figure=fig,
        fmt=dec_fmt,
        verify=lambda: holds(key * len(data), sum(data), {}),
    )


# ---------- TWOVAR: models and scatterplots ----------


@register(S + "TWOVAR.FIT")
def twovar_fit(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "TWOVAR.FIT"
    mv, bv = R(ri(rng, 3, 9), rng.choice([1, 2])), ri(rng, 40, 60)
    xs = sorted(rng.sample(range(1, 11), 8))
    ys = [float(mv * xv + bv) + rng.choice([-4, -3, -2, 2, 3, 4]) for xv in xs]
    fig: dict[str, Any] = {
        "kind": "plot", "x": [0, 11], "y": [0, float(mv * 11 + bv) + 10],
        "curves": [[[0, float(bv)], [11, float(mv * 11 + bv)]]],
        "points": [[xv, yv] for xv, yv in zip(xs, ys, strict=True)],
        "xlabel": "Hours studied", "ylabel": "Test score",
    }  # fmt: skip
    line = f"$y = {tex(mv)}x + {bv}$"
    intro = f"The scatterplot shows hours studied, $x$, and test score, $y$, for 8 students, with the line of best fit {line}."
    if d == "easy":
        t = ri(rng, 2, 10)
        key = mv * t + bv
        stem = f"{intro} According to the line of best fit, what is the predicted score of a student who studied {t} hours?"
        dist = ds(
            (lambda: mv * t, "partial_solution", "Left out the intercept."),
            (lambda: R(bv + t), "misread", "Added the hours instead of multiplying by the slope."),
            (lambda: mv * (t + 1) + bv, "off_by_one", "Evaluated at the wrong $x$."),
            (lambda: R(bv), "misread", "That's the predicted score for 0 hours."),
        )
        steps = [f"$y = {tex(mv)}({t}) + {bv} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            fmt=dec_fmt,
            verify=lambda: holds(key, mv * t + bv, {}),
        )
    if d == "medium":
        i = ri(rng, 0, 7)
        xi, yi = xs[i], R(ys[i]).limit_denominator(10)
        fig["points"][i].append(f"({xi}, {num(yi)})")
        pred = mv * xi + bv
        key = yi - pred
        stem = f"{intro} One student, labeled in the scatterplot, studied {xi} hours and scored ${tex(yi)}$. What is the residual (actual minus predicted) for this student?"
        dist = ds(
            (lambda: pred - yi, "sign_flip", "Residual is actual minus predicted."),
            (lambda: pred, "misread", "That's the predicted score."),
            (lambda: yi - mv * xi, "partial_solution", "Left the intercept out of the prediction."),
            (lambda: yi, "misread", "That's the actual score."),
        )
        steps = [
            f"Predicted: ${tex(mv)}({xi}) + {bv} = {tex(pred)}$.",
            f"Residual: ${tex(yi)} - {tex(pred)} = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            fmt=dec_fmt,
            verify=lambda: holds(pred + key, yi, {}),
        )
    k_ = ri(rng, 2, 5)
    key = mv * k_
    stem = f"{intro} Based on the line of best fit, how much does the predicted score increase for every {k_} additional hours studied?"
    dist = ds(
        (lambda: mv, "partial_solution", "That's the increase for 1 hour."),
        (lambda: mv * k_ + bv, "concept", f"That's the predicted score at {k_} hours, not the change."),
        (lambda: R(bv), "misread", "That's the intercept."),
        (lambda: R(k_, 1) / mv, "reciprocal", "Divided by the slope instead of multiplying."),
    )
    steps = [
        f"The slope ${tex(mv)}$ is the change per hour.",
        f"For {k_} hours: ${tex(mv)} \\times {k_} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        figure=fig,
        fmt=dec_fmt,
        verify=lambda: holds((mv * (5 + k_) + bv) - (mv * 5 + bv), key, {}),
    )


@register(S + "TWOVAR.MODELTYPE")
def twovar_modeltype(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "TWOVAR.MODELTYPE"
    xs = [0, 1, 2, 3]
    a = ri(rng, 2, 9) * rng.choice([1, 10])
    labels = {
        "lin_up": "An increasing linear function",
        "lin_down": "A decreasing linear function",
        "exp_up": "An increasing exponential function",
        "exp_down": "A decreasing exponential function",
    }
    if d in ("easy", "medium"):
        kind = rng.choice(["lin_up", "lin_down"]) if d == "easy" else rng.choice(["exp_up", "exp_down"])
        if kind.startswith("lin"):
            step = ri(rng, 2, 9) * (1 if kind == "lin_up" else -1)
            a = a + 40 if step < 0 else a
            ys = [R(a + step * xv) for xv in xs]
        else:
            b = rng.choice([R(2), R(3), R(3, 2)]) if kind == "exp_up" else rng.choice([R(1, 2), R(1, 3)])
            a = a * 27 * 8 if kind == "exp_down" else a * 8
            ys = [a * b**xv for xv in xs]
        diffs = {ys[i + 1] - ys[i] for i in range(3)}
        ratios = {ys[i + 1] / ys[i] for i in range(3)}
        found = ("lin_" if len(diffs) == 1 else "exp_") + ("up" if ys[1] > ys[0] else "down")
        key = labels[found]
        why = {
            "lin_up": "Constant differences mean linear; check whether $y$ grows by a fixed amount or a fixed factor.",
            "lin_down": "Check the direction and whether the change is a fixed amount or a fixed factor.",
            "exp_up": "Check whether $y$ changes by a fixed factor (exponential) or a fixed amount (linear).",
            "exp_down": "Check the direction and whether the change is a fixed amount or a fixed factor.",
        }
        dist = [D(v, "concept", why[c]) for c, v in labels.items() if c != found]
        fig = {
            "kind": "table",
            "header": ["$x$", "$y$"],
            "rows": [[m(xv), m(yv)] for xv, yv in zip(xs, ys, strict=True)],
        }
        stem = "Which type of function best models the relationship between $x$ and $y$ shown in the table?"
        steps = [f"Differences: {', '.join(m(ys[i + 1] - ys[i]) for i in range(3))}; ratios: {', '.join(m(ys[i + 1] / ys[i]) for i in range(3))}.",
                 "A constant difference means linear; a constant ratio means exponential."]  # fmt: skip
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            fmt=dec_fmt,
            verify=lambda: (
                (len(diffs) == 1) == found.startswith("lin") and (len(ratios) == 1) == found.startswith("exp")
            ),
        )
    b = rng.choice([R(2), R(3), R(1, 2), R(3, 2)])
    a = a * 16
    ys = [a * b**xv for xv in xs]
    c_, r_ = sympy.symbols("c r", positive=True)
    sol = sympy.solve([sympy.Eq(c_, ys[0]), sympy.Eq(c_ * r_, ys[1])], [c_, r_], dict=True)[0]
    key = sol[c_] * sol[r_] ** 5
    fig = {
        "kind": "table",
        "header": ["$x$", "$y$"],
        "rows": [[m(xv), m(yv)] for xv, yv in zip(xs, ys, strict=True)],
    }
    stem = "The table shows values of an exponential function. What is the value of $y$ when $x = 5$?"
    dist = ds(
        (
            lambda: ys[3] + 2 * (ys[3] - ys[2]),
            "wrong_formula",
            "Extended it linearly; the ratio, not the difference, is constant.",
        ),
        (lambda: sol[c_] * sol[r_] ** 4, "off_by_one", "That's the value at $x = 4$."),
        (
            lambda: sol[c_] * sol[r_] * 5,
            "exponent_rule",
            "Multiplied by 5 instead of raising to the 5th power.",
        ),
        (lambda: ys[3] * sol[r_] ** 3, "off_by_one", "Applied the ratio one time too many."),
    )
    steps = [
        f"Ratio: ${tex(sol[r_])}$; initial value ${tex(sol[c_])}$.",
        f"$y = {tex(sol[c_])}({tex(sol[r_])})^5 = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        figure=fig,
        fmt=dec_fmt,
        verify=lambda: holds(ys[3] * b * b, key, {}),
    )


# ---------- PROB ----------


@register(S + "PROB.BASIC")
def prob_basic(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "PROB.BASIC"
    r, b, g = ri(rng, 2, 12), ri(rng, 2, 12), ri(rng, 2, 12)
    tot = r + b + g
    intro = f"A bag contains {r} red, {b} blue, and {g} green marbles."
    if d == "easy":
        key = R(r, tot)
        stem = f"{intro} One marble is chosen at random. What is the probability that it is red?"
        dist = ds(
            (lambda: R(r, b + g), "wrong_formula", "Divided by the non-red marbles; divide by the total."),
            (lambda: R(1, 3), "concept", "The three colors aren't equally likely."),
            (lambda: R(b + g, tot), "misread", "That's the probability of not red."),
            (lambda: R(r, 100), "unit_slip", "Treated the count as a percent."),
        )
        steps = [f"$P = \\frac{{{r}}}{{{tot}}} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: key * tot == r,
        )
    if d == "medium":
        key = R(r + b, tot)
        stem = f"{intro} One marble is chosen at random. What is the probability that it is not green?"
        dist = ds(
            (lambda: R(g, tot), "misread", "That's the probability of green."),
            (
                lambda: R(r * b, tot * tot),
                "concept",
                "Multiplied probabilities; for 'or' with no overlap, add them.",
            ),
            (lambda: R(r + b, g), "wrong_formula", "Divided by the green marbles; divide by the total."),
            (lambda: R(2, 3), "concept", "The colors aren't equally likely."),
        )
        steps = [f"Not green: ${r} + {b} = {r + b}$ of ${tot}$.", f"$P = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: key + R(g, tot) == 1,
        )
    key = R(r, tot) * R(r - 1, tot - 1)
    stem = f"{intro} Two marbles are chosen at random, one after the other, without replacement. What is the probability that both are red?"
    dist = ds(
        (
            lambda: R(r, tot) ** 2,
            "concept",
            "That assumes replacement; the second draw has one fewer marble.",
        ),
        (lambda: R(r * (r - 1), tot * tot), "partial_solution", "Reduced the red count but not the total."),
        (lambda: R(2 * r, tot), "wrong_formula", "Added the probabilities instead of multiplying."),
        (
            lambda: R(r - 1, tot - 1),
            "partial_solution",
            "That's only the second draw, given the first was red.",
        ),
    )
    steps = [
        f"First red: $\\frac{{{r}}}{{{tot}}}$; then $\\frac{{{r - 1}}}{{{tot - 1}}}$.",
        f"Multiply: ${tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=dec_fmt,
        verify=lambda: holds(key, sympy.binomial(r, 2) / sympy.binomial(tot, 2), {}),
    )


COND_CTX = [
    ("students", "student", ("10th grade", "11th grade"), ("Prefer online", "Prefer in person"), "prefers online classes", "is in 10th grade"),
    ("survey respondents", "respondent", ("Urban", "Rural"), ("Own a car", "Don't own a car"), "owns a car", "lives in an urban area"),
    ("plants in an experiment", "plant", ("Fertilizer A", "Fertilizer B"), ("Flowered", "Didn't flower"), "flowered", "received fertilizer A"),
]  # fmt: skip


@register(S + "PROB.COND")
def prob_cond(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "PROB.COND"
    who, one, rows, cols, yes_desc, a_desc = rng.choice(COND_CTX)
    t = [[ri(rng, 5, 60) for _ in range(2)] for _ in range(2)]
    tot = sum(map(sum, t))
    fig = {
        "kind": "table",
        "header": ["", cols[0], cols[1], "Total"],
        "rows": [[rows[0], *map(str, t[0]), str(sum(t[0]))], [rows[1], *map(str, t[1]), str(sum(t[1]))],
                 ["Total", str(t[0][0] + t[1][0]), str(t[0][1] + t[1][1]), str(tot)]],
    }  # fmt: skip
    intro = f"The table summarizes {tot} {who}."
    yes_tot, a_tot = t[0][0] + t[1][0], sum(t[0])
    if d == "easy":
        key = R(yes_tot, tot)
        stem = f"{intro} If one {one} is chosen at random, what is the probability that the {one} {yes_desc}?"
        dist = ds(
            (lambda: R(t[0][0], tot), "partial_solution", f"Counted only the {rows[0]} row."),
            (
                lambda: R(yes_tot, tot - yes_tot),
                "wrong_formula",
                "Divided by the other column instead of the total.",
            ),
            (lambda: R(t[0][0], a_tot), "misread", "That's a conditional probability within one row."),
            (lambda: R(tot - yes_tot, tot), "misread", "That's the complement."),
        )
        steps = [f"$\\frac{{{yes_tot}}}{{{tot}}} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            fmt=dec_fmt,
            verify=lambda: key * tot == yes_tot,
        )
    if d == "medium":
        key = R(t[0][0], a_tot)
        stem = f"{intro} If a {one} that {a_desc} is chosen at random, what is the probability that the {one} {yes_desc}?"
        dist = ds(
            (
                lambda: R(t[0][0], yes_tot),
                "concept",
                "Reversed the condition: that's $P(\\text{row} \\mid \\text{column})$.",
            ),
            (
                lambda: R(t[0][0], tot),
                "misread",
                "Divided by the grand total; the condition restricts to one row.",
            ),
            (lambda: R(yes_tot, tot), "concept", "Ignored the condition."),
            (lambda: R(t[0][1], a_tot), "misread", "That's the other column of the same row."),
        )
        steps = [
            f"Restrict to the {rows[0]} row: {a_tot}.",
            f"$\\frac{{{t[0][0]}}}{{{a_tot}}} = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            fmt=dec_fmt,
            verify=lambda: key * a_tot == t[0][0],
        )
    key = R(t[0][0], yes_tot)
    stem = f"{intro} A {one} that {yes_desc} is chosen at random. What is the probability that the {one} {a_desc}?"
    dist = ds(
        (
            lambda: R(t[0][0], a_tot),
            "concept",
            "Reversed the condition: restrict to the column, not the row.",
        ),
        (lambda: R(t[0][0], tot), "misread", "Divided by the grand total."),
        (lambda: R(a_tot, tot), "concept", "Ignored the condition."),
        (lambda: R(t[1][0], yes_tot), "misread", "Used the other row."),
    )
    steps = [
        f"Restrict to the '{cols[0]}' column: {yes_tot}.",
        f"$\\frac{{{t[0][0]}}}{{{yes_tot}}} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        figure=fig,
        fmt=dec_fmt,
        verify=lambda: key * yes_tot == t[0][0],
    )


# ---------- INFER / CLAIMS ----------


@register(S + "INFER.MOE")
def infer_moe(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "INFER.MOE"
    if d == "easy":
        mu, e = ri(rng, 20, 80), ri(rng, 2, 6)
        key = f"Between {mu - e} and {mu + e} minutes"
        stem = f"A random sample of commuters in a city had a mean commute time of {mu} minutes, with an associated margin of error of {e} minutes. Which is the most appropriate conclusion about the mean commute time of all commuters in the city?"
        dist = [
            D(
                f"Exactly {mu} minutes",
                "concept",
                "A sample estimate isn't exact for the population; that's why there's a margin of error.",
            ),
            D(
                f"Between {mu} and {mu + e} minutes",
                "partial_solution",
                "The margin of error extends both above and below the estimate.",
            ),
            D(
                f"Between {mu - 2 * e} and {mu + 2 * e} minutes",
                "wrong_formula",
                "Doubled the margin of error.",
            ),
            D(
                f"Greater than {mu + e} minutes",
                "misread",
                "Values beyond the margin of error are not plausible.",
            ),
        ]
        steps = [f"Plausible values: ${mu} \\pm {e}$, i.e. from {mu - e} to {mu + e}."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: mu - e < mu < mu + e,
        )
    if d == "medium":
        n1, n2 = rng.sample([100, 200, 400, 600, 900, 1500], 2)
        big = max(n1, n2)
        key = f"The study with {big} participants, because a larger random sample tends to have a smaller margin of error."
        stem = f"Two researchers each select a random sample from the same population to estimate the same mean. One sample has {n1} people and the other has {n2}. Which study is likely to have the smaller margin of error?"
        small = min(n1, n2)
        dist = [
            D(
                f"The study with {small} participants, because a smaller sample has less variability.",
                "concept",
                "Smaller samples give less precise estimates.",
            ),
            D(
                "Both studies, because they sample the same population.",
                "concept",
                "Margin of error depends on sample size, not just the population.",
            ),
            D(
                "Neither: margin of error doesn't depend on sample size.",
                "concept",
                "Larger samples reduce the margin of error.",
            ),
        ]
        steps = ["With everything else equal, a larger random sample yields a smaller margin of error."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            fmt=dec_fmt,
            verify=lambda: big > small,
        )
    p_, e = ri(rng, 20, 70), ri(rng, 2, 5)
    n_pop = ri(rng, 2, 30) * 1000
    key = R(p_ + e, 100) * n_pop
    stem = f"In a random sample of residents of a town of {n_pop} people, {p_}% supported a new park, with a margin of error of {e} percentage points. Based on the sample, what is the greatest plausible number of residents in the town who support the park?"
    dist = ds(
        (
            lambda: R(p_, 100) * n_pop,
            "partial_solution",
            "That's the point estimate; the question asks for the upper end.",
        ),
        (lambda: R(p_ - e, 100) * n_pop, "misread", "That's the least plausible number."),
        (lambda: R(p_ + e) * n_pop, "unit_slip", "Forgot to convert the percent to a decimal."),
        (
            lambda: R(p_, 100) * n_pop + e,
            "unit_slip",
            "Added the margin of error as a number of people, not percentage points.",
        ),
    )
    steps = [
        f"Upper bound: ${p_ + e}\\%$ of ${n_pop}$.",
        f"${(p_ + e) / 100:g} \\times {n_pop} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=dec_fmt,
        verify=lambda: key * 100 == (p_ + e) * n_pop,
    )


CLAIMS_CTX = [
    ("adults in a city", "drink green tea daily", "lower blood pressure", "green tea"),
    ("students at a university", "use a spaced-repetition app", "higher exam scores", "the app"),
    ("employees at a large company", "take a short afternoon walk", "better reported focus", "the walk"),
    ("residents of a county", "take a vitamin D supplement", "fewer sick days", "the supplement"),
]


@register(S + "CLAIMS.DESIGN")
def claims_design(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "CLAIMS.DESIGN"
    pop, act, out, thing = rng.choice(CLAIMS_CTX)
    if d == "easy":
        rs, ra = rng.choice([(True, True), (False, False)])
    elif d == "medium":
        rs, ra = rng.choice([(True, False), (False, True)])
    else:
        rs, ra = rng.choice([(True, True), (True, False), (False, True), (False, False)])
    if rs:
        sel = f"selected 300 {pop} at random"
    elif d == "hard":
        sel = f"invited all {pop} to volunteer and then chose 300 of the volunteers at random"
    else:
        sel = f"recruited 300 {pop} who volunteered"
    if ra:
        asg = f"randomly assigned half of them to {act} and the other half not to"
    elif d == "hard":
        asg = f"compared those who already chose to {act} with those who did not"
    else:
        asg = f"let each participant decide whether to {act}"
    stem = (
        f"Researchers {sel}. They {asg}. After 8 weeks, the group that chose or was assigned to {act} had "
        f"{out} on average. Which conclusion is most appropriate?"
    ).replace("chose or was assigned", "was assigned" if ra else "chose")
    labels = {
        (True, True): f"Taking {thing} likely causes {out} among {pop} in general.",
        (
            False,
            True,
        ): f"Taking {thing} likely causes {out} for people like the participants, but the result can't be generalized to all {pop}.",
        (
            True,
            False,
        ): f"There is an association between {thing} and {out} among {pop}, but it can't be concluded that {thing} causes it.",
        (
            False,
            False,
        ): f"There is an association between {thing} and {out} for the participants only; no causal or general conclusion can be drawn.",
    }
    why = {
        (
            True,
            True,
        ): "Causation needs random assignment and generalizing needs random sampling; this study lacks at least one.",
        (
            False,
            True,
        ): "Check whether the participants were randomly sampled and whether treatments were randomly assigned.",
        (
            True,
            False,
        ): "Check whether the participants were randomly sampled and whether treatments were randomly assigned.",
        (
            False,
            False,
        ): "This study has random sampling or random assignment, which supports a stronger conclusion.",
    }
    key = labels[(rs, ra)]
    dist = [D(v, "concept", why[c]) for c, v in labels.items() if c != (rs, ra)]
    steps = [
        "Random selection from the population lets results generalize to that population.",
        "Random assignment to groups lets you conclude cause and effect.",
        f"Here: random sampling {'yes' if rs else 'no'}{' (the 300 were chosen from volunteers)' if not rs and d == 'hard' else ''}, random assignment {'yes' if ra else 'no'}.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=dec_fmt,
        verify=lambda: (
            ("random" in sel and "volunteer" not in sel) == rs and ("randomly assigned" in asg) == ra
        ),
    )
