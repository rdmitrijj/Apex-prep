"""Algebra generators (MATH.ALG.*)."""

import random
from typing import Any

import sympy

from app.generators.core import (
    D,
    Difficulty,
    Generated,
    R,
    Value,
    build,
    ds,
    holds,
    k,
    lin,
    m,
    pt,
    register,
    ri,
    tex,
    x,
    y,
)

S = "MATH.ALG."
NSOL_CHOICES = {
    "zero": "Zero",
    "one": "Exactly one",
    "two": "Exactly two",
    "inf": "Infinitely many",
}
NSOL_WHY = {
    "zero": "There is a solution: the variable terms don't cancel (or they cancel to a true statement).",
    "one": "The variable terms cancel, so the equation can't pin down a single value.",
    "two": "A linear equation (or system of lines) can't have exactly two solutions.",
    "inf": "After simplifying, the two sides are not identical, so not every value works.",
}


def _nsol_choices(key: str) -> list[D]:
    return [D(v, "concept", NSOL_WHY[c]) for c, v in NSOL_CHOICES.items() if c != key]


def _count_linear(expr: sympy.Expr, var: sympy.Symbol) -> str:
    """Number of solutions of expr = 0 for linear expr: SymPy decides."""
    p = sympy.Poly(sympy.expand(expr), var)
    if p.degree() >= 1:
        return "one"
    return "inf" if sympy.expand(expr) == 0 else "zero"


# ---------- LIN1: linear equations in one variable ----------


@register(S + "LIN1.SOLVE")
def lin1_solve(rng: random.Random, d: Difficulty) -> Generated:
    if d == "easy":
        a, sol, b = ri(rng, 2, 9), ri(rng, -9, 12), ri(rng, -15, 15)
        c = a * sol + b
        lhs, rhs = a * x + b, sympy.Integer(c)
        key = sympy.solve(sympy.Eq(lhs, rhs), x)[0]
        dist = ds(
            (
                lambda: R(c + b, a),
                "sign_flip",
                f"Moved ${b}$ across the equals sign without changing its sign.",
            ),
            (lambda: R(c - b), "partial_solution", f"${c - b}$ is the value of ${a}x$, not $x$."),
            (lambda: R(c, a) - b, "order_of_ops", "Divided before subtracting the constant."),
            (lambda: R(a * (c - b)), "operation_swap", f"Multiplied by ${a}$ instead of dividing."),
        )
        steps = [f"Subtract ${b}$ from both sides: ${a}x = {c - b}$.", f"Divide by ${a}$: $x = {tex(key)}$."]
        disp = f"{lin(a, b)} = {c}"
    elif d == "medium":
        a, b, c = ri(rng, 2, 7), ri(rng, -9, 9), ri(rng, -6, 6)
        while c == a:
            c = ri(rng, -6, 6)
        sol = ri(rng, -8, 10)
        e = a * (sol + b) - c * sol
        lhs, rhs = a * (x + b), c * x + e
        key = sympy.solve(sympy.Eq(lhs, rhs), x)[0]
        dist = ds(
            (lambda: R(e - b, a - c), "distribution", f"Multiplied only $x$ by ${a}$, not the ${b}$."),
            (lambda: R(e + a * b, a - c), "sign_flip", f"Moved ${a * b}$ across without changing its sign."),
            (lambda: R(e - a * b, a + c), "sign_flip", f"Moved ${c}x$ across without changing its sign."),
            (lambda: R((a - c) * sol), "partial_solution", f"This is the value of ${a - c}x$, not $x$."),
        )
        disp = f"{a}({lin(1, b)}) = {lin(c, e)}"
        steps = [
            f"Distribute: ${a}x {'+' if a * b >= 0 else '-'} {abs(a * b)} = {lin(c, e)}$.",
            f"Collect $x$ terms: ${a - c}x = {e - a * b}$.",
            f"Divide: $x = {tex(key)}$.",
        ]
    else:
        p, s_ = rng.sample([2, 3, 4, 5, 6], 2)
        u, v, w = ri(rng, -7, 7), ri(rng, -7, 7), ri(rng, -5, 5)
        lhs, rhs = R(1, p) * (x + u) - R(1, s_) * (x - v), sympy.Integer(w)
        key = sympy.solve(sympy.Eq(lhs, rhs), x)[0]
        dist = ds(
            (
                lambda: sympy.solve(sympy.Eq(R(1, p) * (x + u) - R(1, s_) * (x + v), w), x)[0],
                "sign_flip",
                f"Didn't distribute the minus sign to the ${-v}$ inside the second fraction.",
            ),
            (
                lambda: sympy.solve(sympy.Eq(s_ * (x + u) - p * (x - v), w), x)[0],
                "distribution",
                f"Cleared denominators but didn't multiply the right side by ${p * s_}$.",
            ),
            (
                lambda: key + u,
                "misread",
                f"This is the value of $x {'+' if u >= 0 else '-'} {abs(u)}$, not $x$.",
            ),
            (
                lambda: sympy.solve(sympy.Eq(R(1, p) * (x + u) + R(1, s_) * (x - v), w), x)[0],
                "sign_flip",
                "Added the fractions instead of subtracting.",
            ),
        )
        disp = f"\\frac{{{lin(1, u)}}}{{{p}}} - \\frac{{{lin(1, -v)}}}{{{s_}}} = {w}"
        steps = [
            f"Multiply both sides by ${p * s_}$: ${s_}(x {'+' if u >= 0 else '-'} {abs(u)}) - {p}(x "
            f"{'-' if v >= 0 else '+'} {abs(v)}) = {p * s_ * w}$.",
            f"Simplify and solve: $x = {tex(key)}$.",
        ]
    stem = f"$${disp}$$ What value of $x$ is the solution to the equation above?"
    return build(
        rng,
        skill=S + "LIN1.SOLVE",
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(lhs, rhs, {x: key}),
    )


@register(S + "LIN1.NSOL")
def lin1_nsol(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LIN1.NSOL"
    key: Value
    if d == "easy":
        a, b = ri(rng, 2, 8), ri(rng, -9, 9)
        case = rng.choice(["zero", "one", "inf"])
        c = a if case != "one" else a + ri(rng, 1, 3)
        e = a * b if case == "inf" else a * b + ri(rng, 1, 9) * rng.choice([-1, 1])
        lhs, rhs = a * (x + b), c * x + e
        key = NSOL_CHOICES[_count_linear(lhs - rhs, x)]
        stem = f"$${a}({lin(1, b)}) = {lin(c, e)}$$ How many solutions does the equation above have?"
        steps = [
            f"Expand the left side: ${tex(sympy.expand(lhs))} = {tex(rhs)}$.",
            f"Subtract the right side: ${tex(sympy.expand(lhs - rhs))} = 0$.",
            {
                "zero": "The $x$ terms cancel and leave a false statement, so there is no solution.",
                "inf": "Everything cancels to $0 = 0$, which is always true: infinitely many solutions.",
                "one": "The $x$ terms don't cancel, so there is exactly one solution.",
            }[_count_linear(lhs - rhs, x)],
        ]

        def verify() -> bool:
            sols = sympy.solve(sympy.Eq(lhs, rhs), x)
            if case == "one":
                return len(sols) == 1
            same = [holds(lhs, rhs, {x: t}) for t in (0, 1, 7)]
            return all(same) if case == "inf" else not any(same)

        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=_nsol_choices([c_ for c_, v in NSOL_CHOICES.items() if v == key][0]),
            steps=steps,
            verify=verify,
        )
    if d == "medium":
        a, p_, b = ri(rng, 2, 6), ri(rng, 2, 5), ri(rng, -8, 8)
        e = a * b + ri(rng, 1, 9)
        lhs, rhs = a * (p_ * x + b), k * x + e
        coeff = sympy.Poly(sympy.expand(lhs - rhs), x).coeff_monomial(x)
        key = sympy.solve(sympy.Eq(coeff, 0), k)[0]
        dist = ds(
            (lambda: R(p_), "distribution", f"Didn't multiply ${p_}x$ by ${a}$."),
            (lambda: -key, "sign_flip", "Sign error when moving $kx$ to the other side."),
            (lambda: R(a + p_), "operation_swap", f"Added ${a}$ and ${p_}$ instead of multiplying."),
            (lambda: R(e, b) if b else R(e), "concept", "Matched constants instead of $x$-coefficients."),
        )
        stem = (
            f"$${a}({lin(p_, b)}) = kx + {e}$$ In the equation above, $k$ is a constant. If the equation has "
            "no solution, what is the value of $k$?"
        )
        steps = [
            f"Expand: ${tex(sympy.expand(lhs))} = kx + {e}$.",
            "No solution means the $x$ terms cancel while the constants differ.",
            f"So $k = {a * p_}$ (and ${a * b} \\ne {e}$, so the constants really differ).",
        ]

        def verify() -> bool:
            dif = sympy.expand((lhs - rhs).subs(k, key))
            return bool(dif.is_number and dif != 0)

        return build(rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps, verify=verify)
    m_, n_, p_ = ri(rng, 2, 5), ri(rng, 2, 4), ri(rng, -4, 6)
    k0 = R(ri(rng, -9, 9), rng.choice([1, 1, 2, 3]))
    q_, r_ = m_ * n_ + p_, -m_ * k0
    lhs, rhs = m_ * (n_ * x - k) + p_ * x, q_ * x + r_
    key = sympy.solve(sympy.Eq(sympy.expand(lhs - rhs).subs(x, 0), 0), k)[0]
    dist = ds(
        (lambda: -key, "sign_flip", "Sign error with the $-k$ inside the parentheses."),
        (lambda: -r_, "partial_solution", f"Forgot to divide by ${m_}$ after distributing."),
        (lambda: R(-r_, m_ * n_), "distribution", f"Multiplied $k$ by ${m_ * n_}$ instead of ${m_}$."),
        (lambda: R(q_ - p_, m_), "concept", "Matched $x$-coefficients, which already agree for any $k$."),
    )
    stem = (
        f"$${m_}({n_}x - k){'' if p_ == 0 else f' + {p_}x' if p_ > 0 else f' - {-p_}x'} = {lin(q_, r_)}$$ "
        "In the equation above, $k$ is a constant. If the equation has infinitely many solutions, what is the value of $k$?"
    )
    steps = [
        f"Expand the left side: ${tex(sympy.expand(lhs))}$.",
        f"The $x$-coefficients already match (${q_}$). Infinitely many solutions needs the constants to "
        f"match too: $-{m_}k = {tex(r_)}$.",
        f"$k = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: sympy.expand((lhs - rhs).subs(k, key)) == 0,
    )


SERVICES = [
    ("An electrician", "a service fee", "hour"),
    ("A bike rental shop", "a deposit", "day"),
    ("A moving company", "a booking fee", "hour"),
    ("A gym", "a joining fee", "month"),
    ("A storage company", "a setup fee", "week"),
]


@register(S + "LIN1.MODEL")
def lin1_model(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LIN1.MODEL"
    who, fee_name, unit = rng.choice(SERVICES)
    f, r = ri(rng, 3, 12) * 5, ri(rng, 3, 15) * 2
    if d == "easy":
        h = ri(rng, 2, 12)
        t = f + r * h
        key = sympy.solve(sympy.Eq(f + r * x, t), x)[0]
        stem = (
            f"{who} charges {fee_name} of \\${f} plus \\${r} per {unit}. A customer's total charge was "
            f"\\${t}. For how many {unit}s was the customer charged?"
        )
        dist = ds(
            (lambda: R(t + f, r), "sign_flip", f"Added the \\${f} instead of subtracting it."),
            (
                lambda: R(t - f),
                "partial_solution",
                f"\\${t - f} is the charge for the {unit}s, not the count.",
            ),
            (lambda: R(t, r), "misread", f"Ignored the \\${f} {fee_name}."),
            (lambda: R(t, r) - f, "order_of_ops", "Divided before subtracting the fee."),
        )
        steps = [f"${f} + {r}n = {t}$", f"${r}n = {t - f}$", f"$n = {tex(key)}$"]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: f + r * key == t,
        )
    if d == "medium":
        n = sympy.Symbol("n")
        key_expr = r * n + f
        key = f"$T = {lin(r, f, 'n')}$"
        stem = (
            f"{who} charges {fee_name} of \\${f} plus \\${r} per {unit}. Which equation gives the total "
            f"charge $T$, in dollars, for $n$ {unit}s?"
        )
        dist = [
            D(f"$T = {lin(f, r, 'n')}$", "misread", "Swapped the one-time fee and the per-unit rate."),
            D(f"$T = {r}(n + {f})$", "distribution", f"This multiplies the fee by ${r}$ too."),
            D(f"$T = {lin(r, -f, 'n')}$", "sign_flip", "The fee is added to the cost, not subtracted."),
            D(f"$T = {lin(r + f, 0, 'n')}$", "wrong_formula", f"Charges the fee every {unit}."),
        ]
        steps = [
            f"Each {unit} adds \\${r}, so $n$ {unit}s cost ${r}n$.",
            f"Add the one-time \\${f}: $T = {r}n + {f}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key_expr.subs(n, 3) == f + r + r + r,
        )
    a, b = ri(rng, 2, 20) * 10, ri(rng, 22, 50) * 10
    q_ = ri(rng, 2, 6) * 5
    w = ri(rng, 3, 12)
    p_ = q_ + R(b - a, w)
    while not p_.is_integer:
        w = ri(rng, 3, 12)
        b = a + w * ri(rng, 1, 6) * 5
        p_ = q_ + R(b - a, w)
    key = sympy.solve(sympy.Eq(a + p_ * x, b + q_ * x), x)[0]
    stem = (
        f"Ana has \\${a} in savings and adds \\${p_} each week. Ben has \\${b} and adds \\${q_} each week. "
        "After how many weeks will they have the same amount?"
    )
    dist = ds(
        (
            lambda: R(b - a, p_ + q_),
            "wrong_formula",
            "Added the weekly amounts; the gap closes by their difference.",
        ),
        (lambda: R(a + b, p_ - q_), "sign_flip", "Added the starting amounts instead of subtracting."),
        (
            lambda: R(b - a),
            "partial_solution",
            "That's the starting gap in dollars, not the number of weeks.",
        ),
        (lambda: R(b - a, q_), "misread", "Divided by Ben's rate instead of the difference in rates."),
    )
    steps = [f"${a} + {p_}w = {b} + {q_}w$", f"${p_ - q_}w = {b - a}$", f"$w = {tex(key)}$"]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: a + p_ * key == b + q_ * key,
    )


# ---------- LIN2: linear equations in two variables ----------

INTERP = [
    {
        "desc": "The total cost $C$, in dollars, to rent a kayak for $h$ hours is given by $C = {m}h + {b}$.",
        "slope": "The cost, in dollars, per hour of rental",
        "icpt": "The fixed cost, in dollars, charged for any rental",
        "total": "The total cost, in dollars, of renting for $h$ hours",
        "var": "The number of hours the kayak is rented",
    },
    {
        "desc": "A phone plan's monthly bill $B$, in dollars, for $g$ gigabytes of data is $B = {m}g + {b}$.",
        "slope": "The charge, in dollars, for each gigabyte of data",
        "icpt": "The monthly charge, in dollars, before any data is used",
        "total": "The total monthly bill, in dollars",
        "var": "The number of gigabytes used in a month",
    },
    {
        "desc": "The height $H$, in centimeters, of a plant $d$ days after it was measured is $H = {m}d + {b}$.",
        "slope": "The growth of the plant, in centimeters, per day",
        "icpt": "The height of the plant, in centimeters, when it was first measured",
        "total": "The height of the plant, in centimeters, after $d$ days",
        "var": "The number of days since the plant was first measured",
    },
    {
        "desc": "The number of liters $L$ of water in a tank $t$ minutes after a pump starts filling it is "
        "$L = {m}t + {b}$.",
        "slope": "The rate, in liters per minute, at which the pump fills the tank",
        "icpt": "The amount of water, in liters, in the tank when the pump started",
        "total": "The amount of water, in liters, in the tank after $t$ minutes",
        "var": "The number of minutes the pump has run",
    },
]


@register(S + "LIN2.INTERP")
def lin2_interp(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LIN2.INTERP"
    if d in ("easy", "medium"):
        c = rng.choice(INTERP)
        mv, bv = ri(rng, 2, 40), ri(rng, 5, 90)
        ask = "slope" if d == "easy" else "icpt"
        num = mv if ask == "slope" else bv
        other = "icpt" if ask == "slope" else "slope"
        stem = c["desc"].format(m=mv, b=bv) + f" What is the best interpretation of ${num}$ in this context?"
        dist = [
            D(c[other], "concept", "Confused the rate of change with the starting value."),
            D(c["total"], "misread", "That is what the whole expression represents, not this number."),
            D(c["var"], "misread", "That is what the variable represents."),
        ]
        steps = [
            f"In a linear model, the coefficient of the variable (${mv}$) is the rate of change; "
            f"the constant (${bv}$) is the value when the variable is 0.",
            f"So ${num}$ is: {c[ask].lower()}.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=c[ask],
            distractors=dist,
            steps=steps,
            verify=lambda: str(num) in stem,
        )
    ca, cb = rng.sample([2, 3, 4, 5, 6, 8, 9, 10, 12, 15], 2)
    t = ca * cb * ri(rng, 4, 12)
    step = rng.choice([2, 3, 4, 5, 6])
    a_, b_ = sympy.symbols("a b")
    b_of_a = sympy.solve(sympy.Eq(ca * a_ + cb * b_, t), b_)[0]
    key = -sympy.diff(b_of_a, a_) * step
    stem = (
        f"A theater sells adult tickets for \\${ca} and student tickets for \\${cb}. The equation "
        f"${ca}a + {cb}b = {t}$ describes combinations of $a$ adult and $b$ student tickets with total "
        f"sales of \\${t}. If the number of adult tickets increases by {step} and total sales stay "
        "the same, by how much does the number of student tickets decrease?"
    )
    dist = ds(
        (lambda: R(cb * step, ca), "reciprocal", "Used the ratio of prices upside down."),
        (lambda: R(ca * step), "partial_solution", "That's the extra adult revenue in dollars."),
        (lambda: R(ca, cb), "misread", f"That's the decrease for 1 more adult ticket, not {step}."),
        (lambda: R(step), "concept", "Assumed the counts trade one-for-one; prices differ."),
    )
    steps = [
        f"{step} more adult tickets add \\${ca * step} in sales.",
        f"To keep total sales fixed, student sales drop by \\${ca * step}, i.e. "
        f"${ca * step} \\div {cb} = {tex(key)}$ tickets.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(ca * (3 + step) + cb * (b_of_a.subs(a_, 3) - key), t, {}),
    )


@register(S + "LIN2.SOLN")
def lin2_soln(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LIN2.SOLN"
    key: Value
    a, b = ri(rng, 2, 7), ri(rng, -7, 7)
    x0, y0 = ri(rng, -6, 8), ri(rng, -6, 8)
    c = a * x0 + b * y0
    eq_tex = f"{lin(a, 0)} {'+' if b > 0 else '-'} {abs(b) if abs(b) != 1 else ''}y = {c}"

    def on(px: int, py: int) -> bool:
        return a * px + b * py == c

    if d == "easy":
        key = pt(x0, y0)
        cands = [
            ((y0, x0), "misread", "The coordinates are swapped."),
            ((x0, -y0), "sign_flip", "Sign error on $y$."),
            ((x0 + 1, y0), "off_by_one", "Check it: substituting gives a different value."),
            ((-x0, y0), "sign_flip", "Sign error on $x$."),
            ((x0, y0 + 1), "off_by_one", "Check it: substituting gives a different value."),
        ]
        dist = [D(pt(*p), mo, why) for p, mo, why in cands if not on(*p)]
        stem = f"$${eq_tex}$$ Which point $(x, y)$ is a solution to the equation above?"
        steps = [f"Substitute each point. ${a}({x0}) + {tex(b)}({y0}) = {c}$, so ${tex(key)[1:-1]}$ works."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: on(x0, y0),
        )
    if d == "medium":
        key = sympy.solve(sympy.Eq(a * x + b * y0, c), x)[0]
        dist = ds(
            (lambda: R(c + b * y0, a), "sign_flip", f"Moved ${b * y0}$ across without changing its sign."),
            (lambda: R(c - b * y0), "partial_solution", f"That's the value of ${a}x$."),
            (lambda: R(c - b, a), "misread", "Forgot to multiply the coefficient of $y$ by the $y$-value."),
            (lambda: R(y0), "misread", "That's the $y$-coordinate."),
        )
        stem = f"$${eq_tex}$$ The point $(a, {y0})$ lies on the graph of the equation above. What is the value of $a$?"
        steps = [
            f"Substitute $y = {y0}$: ${a}a {'+' if b * y0 >= 0 else '-'} {abs(b * y0)} = {c}$.",
            f"$a = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: a * key + b * y0 == c,
        )
    h = ri(rng, 2, 9)
    t = sympy.Symbol("t")
    p_, q_ = sympy.symbols("p q")
    key = sympy.solve(sympy.Eq(a * (p_ + h) + b * (q_ + t), a * p_ + b * q_), t)[0]
    dist = ds(
        (lambda: -key, "sign_flip", "The sign of the change is wrong: the slope is $-a/b$."),
        (lambda: R(-b * h, a), "reciprocal", "Used $b/a$ instead of $a/b$."),
        (
            lambda: R(-a, b),
            "partial_solution",
            f"That's the slope, the change in $y$ per 1 unit of $x$, not per {h}.",
        ),
        (lambda: R(-a * h), "misread", "Forgot to divide by the coefficient of $y$."),
    )
    stem = (
        f"$${eq_tex}$$ The points $(p, q)$ and $(p + {h}, q + t)$ both lie on the line above. "
        "What is the value of $t$?"
    )
    steps = [
        f"Subtract the two substitutions: ${a}({h}) + {tex(b)}t = 0$.",
        f"$t = {tex(key)}$ (the slope $-\\tfrac{{{a}}}{{{b}}}$ times ${h}$).",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(a * (x0 + h) + b * (y0 + key), c, {}),
    )


@register(S + "LIN2.MODEL")
def lin2_model(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LIN2.MODEL"
    if d == "easy":
        pa, ps = rng.sample(range(6, 25), 2)
        t = pa * ri(rng, 3, 20) + ps * ri(rng, 3, 20)
        expr = pa * x + ps * y
        key = f"${pa}x + {ps}y = {t}$"
        stem = (
            f"A museum charges \\${pa} per adult and \\${ps} per student. One day it collected \\${t} from "
            "$x$ adults and $y$ students. Which equation represents this situation?"
        )
        dist = [
            D(f"${ps}x + {pa}y = {t}$", "misread", "The prices are attached to the wrong variables."),
            D(f"$x + y = {t}$", "concept", f"This counts people, but \\${t} is money collected."),
            D(f"${pa + ps}(x + y) = {t}$", "wrong_formula", "Charges every visitor both prices."),
            D(
                f"$\\frac{{x}}{{{pa}}} + \\frac{{y}}{{{ps}}} = {t}$",
                "operation_swap",
                "Divided by the prices instead of multiplying.",
            ),
        ]
        steps = [
            f"Adults bring in ${pa}x$ dollars and students ${ps}y$ dollars.",
            f"Total: ${pa}x + {ps}y = {t}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: expr.subs({x: 2, y: 3}) == 2 * pa + 3 * ps,
        )
    if d == "medium":
        mp = ri(rng, 2, 5)
        per, pp = rng.choice([(4, 6), (6, 9), (5, 8), (3, 4), (12, 15)])
        t = ri(rng, 30, 90)
        expr = mp * x + R(pp, per) * y
        key = f"${mp}x + {tex(R(pp, per))}y = {t}$"
        stem = (
            f"A bakery sells muffins for \\${mp} each and cookies in packs of {per} for \\${pp} per pack. "
            f"A caterer spends \\${t} on $x$ muffins and $y$ individual cookies (in full packs). "
            "Which equation represents this situation?"
        )
        dist = [
            D(f"${mp}x + {pp}y = {t}$", "unit_slip", f"\\${pp} is the price of a pack, not of one cookie."),
            D(
                f"${mp}x + {per * pp}y = {t}$",
                "unit_slip",
                "Multiplied by the pack size instead of dividing.",
            ),
            D(
                f"${mp}x + {tex(R(per, pp))}y = {t}$",
                "reciprocal",
                "This is cookies per dollar, not dollars per cookie.",
            ),
            D(f"$x + y = {t}$", "concept", "This counts items, but the total is in dollars."),
        ]
        steps = [f"One cookie costs $\\frac{{{pp}}}{{{per}}}$ dollars.", f"Total: {key}."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: expr.subs({x: 1, y: per}) == mp + pp,
        )
    pa, pr = ri(rng, 6, 14), ri(rng, 3, 9)
    t = ri(rng, 20, 60)
    expr = R(pa, 16) * x + R(pr, 16) * y
    key = f"$\\frac{{{pa}}}{{16}}x + \\frac{{{pr}}}{{16}}y = {t}$"
    stem = (
        f"Almonds cost \\${pa} per pound and raisins cost \\${pr} per pound. A shopper spends \\${t} on "
        "$x$ ounces of almonds and $y$ ounces of raisins. Which equation represents this situation? "
        "(1 pound = 16 ounces)"
    )
    dist = [
        D(f"${pa}x + {pr}y = {t}$", "unit_slip", "The prices are per pound but $x$ and $y$ are in ounces."),
        D(f"${16 * pa}x + {16 * pr}y = {t}$", "unit_slip", "Multiplied by 16 instead of dividing."),
        D(
            f"$\\frac{{{pa}}}{{16}}x + {pr}y = {t}$",
            "partial_solution",
            "Converted only the almonds to ounces.",
        ),
        D(
            f"$\\frac{{x}}{{{pa}}} + \\frac{{y}}{{{pr}}} = {t}$",
            "operation_swap",
            "Divided by the prices instead of multiplying.",
        ),
    ]
    steps = [
        f"Per ounce: almonds $\\frac{{{pa}}}{{16}}$, raisins $\\frac{{{pr}}}{{16}}$ dollars.",
        f"Total: {key}.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: expr.subs({x: 16, y: 32}) == pa + 2 * pr,
    )


# ---------- LINF: linear functions ----------


@register(S + "LINF.SLOPE")
def linf_slope(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LINF.SLOPE"
    x1, x2 = rng.sample(range(-6, 9), 2)
    mv = R(ri(rng, -6, 6), rng.choice([1, 1, 2, 3]))
    if d == "hard":
        mv = R(ri(rng, -5, 5), rng.choice([2, 3]))
        x1 = x1 - x1 % mv.q
        x2 = x1 + mv.q * ri(rng, 1, 3)
    bv = ri(rng, -6, 6)
    y1, y2 = mv * x1 + bv, mv * x2 + bv
    if d == "easy":
        key = sympy.Rational(y2 - y1, x2 - x1)
        stem = (
            f"A line passes through the points {pt(x1, y1)} and {pt(x2, y2)}. What is the slope of the line?"
        )
        dist = ds(
            (lambda: R(x2 - x1, y2 - y1), "reciprocal", "Run over rise: the slope is rise over run."),
            (lambda: R(y2 - y1, x1 - x2), "sign_flip", "Subtracted the coordinates in opposite orders."),
            (lambda: R(y2 - y1), "partial_solution", "That's only the change in $y$."),
            (lambda: R(y2 + y1, x2 + x1), "wrong_formula", "Added coordinates instead of subtracting."),
            (lambda: -key, "sign_flip", "Sign error."),
        )
        steps = [f"$m = \\frac{{{tex(y2)} - ({tex(y1)})}}{{{x2} - ({x1})}} = {tex(key)}$"]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key * (x2 - x1) == y2 - y1,
        )
    if d == "medium":
        step = ri(rng, 1, 3)
        xs = [x1 + i * step for i in range(3)]
        ys = [mv * xv + bv for xv in xs]
        key = sympy.solve(sympy.Eq(ys[0], (ys[1] - ys[0]) / step * xs[0] + y), y)[0]
        stem = (
            "The table shows three values of $x$ and the corresponding values of $y$ for a linear "
            "relationship. What is the $y$-intercept of the graph of this relationship in the $xy$-plane? "
            "(Give the $y$-coordinate.)"
        )
        fig: dict[str, Any] = {
            "kind": "table",
            "header": ["$x$", "$y$"],
            "rows": [[m(a), m(b)] for a, b in zip(xs, ys, strict=True)],
        }
        dist = ds(
            (lambda: ys[0], "misread", "That's the first $y$-value in the table, not where $x = 0$."),
            (lambda: mv, "misread", "That's the slope."),
            (lambda: ys[0] + mv * xs[0], "sign_flip", "Added $mx$ instead of subtracting it."),
            (lambda: -key, "sign_flip", "Sign error."),
        )
        steps = [
            f"Slope: $\\frac{{{tex(ys[1])} - ({tex(ys[0])})}}{{{step}}} = {tex(mv)}$.",
            f"$b = y - mx = {tex(ys[0])} - ({tex(mv)})({xs[0]}) = {tex(key)}$.",
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
            verify=lambda: all(mv * a + key == b for a, b in zip(xs, ys, strict=True)),
        )
    if mv == 0:
        mv = R(1, 2)
        y1, y2 = mv * x1 + bv, mv * x2 + bv
    key = sympy.solve(sympy.Eq(mv * x + bv, 0), x)[0]
    stem = "The graph of the linear function $f$ is shown, passing through the two labeled points. What is the $x$-intercept of the graph? (Give the $x$-coordinate.)"
    lo, hi = min(x1, x2, float(key), 0) - 2, max(x1, x2, float(key), 0) + 2
    fig = {
        "kind": "plot",
        "x": [lo, hi],
        "y": [min(float(y1), float(y2), 0, bv) - 2, max(float(y1), float(y2), 0, bv) + 2],
        "curves": [[[lo, float(mv * lo + bv)], [hi, float(mv * hi + bv)]]],
        "points": [[x1, float(y1), f"({x1}, {y1})"], [x2, float(y2), f"({x2}, {y2})"]],
    }
    dist = ds(
        (lambda: R(bv), "misread", "That's the $y$-intercept."),
        (lambda: R(bv) / mv, "sign_flip", "Solved $mx + b = 0$ but dropped the negative sign."),
        (lambda: -mv / bv, "reciprocal", "Divided the slope by the intercept instead."),
        (lambda: mv, "misread", "That's the slope."),
    )
    steps = [
        f"Slope: $\\frac{{{tex(y2)} - ({tex(y1)})}}{{{x2} - ({x1})}} = {tex(mv)}$; intercept $b = {bv}$.",
        f"Set $f(x) = 0$: ${tex(mv)}x {'+' if bv >= 0 else '-'} {abs(bv)} = 0$, so $x = {tex(key)}$.",
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
        verify=lambda: holds(y1 + mv * (key - x1), 0, {}),
    )


@register(S + "LINF.NOTATION")
def linf_notation(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LINF.NOTATION"
    a, b = ri(rng, -7, 9, (0, 1)), ri(rng, -12, 12)
    f = a * x + b
    if d == "easy":
        t = ri(rng, -6, 8, (0, 1))
        key = f.subs(x, t)
        stem = f"The function $f$ is defined by $f(x) = {lin(a, b)}$. What is the value of $f({t})$?"
        dist = ds(
            (lambda: a * (t + b), "distribution", "Added the constant before multiplying."),
            (lambda: a * t - b, "sign_flip", "Sign error on the constant."),
            (lambda: R(a * t), "partial_solution", "Forgot to add the constant."),
            (
                lambda: a + b * t,
                "misread",
                "Multiplied the constant by the input instead of the coefficient.",
            ),
        )
        steps = [f"$f({t}) = {a}({t}) {'+' if b >= 0 else '-'} {abs(b)} = {tex(key)}$"]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key == a * t + b,
        )
    if d == "medium":
        v = a * ri(rng, -6, 9) + b
        key = sympy.solve(sympy.Eq(f, v), x)[0]
        stem = (
            f"The function $f$ is defined by $f(x) = {lin(a, b)}$. For what value of $x$ does $f(x) = {v}$?"
        )
        dist = ds(
            (lambda: a * v + b, "misread", f"This is $f({v})$, not the input that gives ${v}$."),
            (lambda: R(v + b, a), "sign_flip", "Sign error when moving the constant."),
            (lambda: R(v - b), "partial_solution", f"Forgot to divide by ${a}$."),
            (lambda: R(v, a) - b, "order_of_ops", "Divided before subtracting."),
        )
        steps = [f"${lin(a, b)} = {v}$", f"$x = {tex(key)}$"]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: f.subs(x, key) == v,
        )
    p_, q_, r_ = rng.sample(range(-5, 10), 3)
    a = R(ri(rng, -6, 6), rng.choice([1, 2]))
    f = a * x + b
    u, v = f.subs(x, p_), f.subs(x, q_)
    s, c = sympy.symbols("s c")
    sol = sympy.solve([sympy.Eq(s * p_ + c, u), sympy.Eq(s * q_ + c, v)], [s, c])
    key = sol[s] * r_ + sol[c]
    stem = (
        f"For the linear function $f$, $f({p_}) = {tex(u)}$ and $f({q_}) = {tex(v)}$. "
        f"What is the value of $f({r_})$?"
    )
    dist = ds(
        (lambda: sol[s], "partial_solution", "That's the slope of $f$."),
        (lambda: sol[c], "misread", "That's $f(0)$, the $y$-intercept."),
        (
            lambda: -sol[s] * r_ + sol[c],
            "sign_flip",
            "Slope sign error: compute $(f(b) - f(a))/(b - a)$ consistently.",
        ),
        (
            lambda: u * R(r_, p_) if p_ else None,
            "wrong_formula",
            "Assumed $f$ is proportional (no intercept).",
        ),
    )
    steps = [
        f"Slope: $\\frac{{{tex(v)} - ({tex(u)})}}{{{q_} - ({p_})}} = {tex(sol[s])}$.",
        f"Intercept: $f(0) = {tex(sol[c])}$.",
        f"$f({r_}) = {tex(sol[s])}({r_}) + ({tex(sol[c])}) = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(f.subs(x, r_), key, {}),
    )


@register(S + "LINF.PARPERP")
def linf_parperp(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LINF.PARPERP"
    if d == "easy":
        mv, bv = R(ri(rng, -7, 7), rng.choice([1, 2, 3, 4])), ri(rng, -9, 9)
        key = mv
        stem = (
            f"Line $\\ell$ is defined by $y = {lin(mv, bv)}$. Line $p$ is "
            "parallel to line $\\ell$. What is the slope of line $p$?"
        )
        dist = ds(
            (lambda: -1 / mv, "concept", "That's the slope of a perpendicular line."),
            (lambda: -mv, "sign_flip", "Parallel lines have the same slope, sign included."),
            (lambda: R(bv), "misread", "That's the $y$-intercept."),
            (lambda: 1 / mv, "reciprocal", "Parallel lines have equal slopes, not reciprocal ones."),
        )
        steps = ["Parallel lines have equal slopes.", f"Slope $= {tex(mv)}$."]
        return build(
            rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps, verify=lambda: key == mv
        )
    a, b = ri(rng, -9, 9), ri(rng, 2, 9)
    c = ri(rng, -20, 20)
    line_slope = -sympy.solve(sympy.Eq(a * x + b * y, c), y)[0].coeff(x) * -1
    perp = -1 / line_slope
    eq = f"{lin(a, 0)} + {b}y = {c}".replace("+ -", "- ")
    solve_y = (
        f"Solve for $y$: ${b}y = {lin(-a, c)}$, so $y = {lin(line_slope, R(c, b))}$. "
        f"The slope of $\\ell$ is the coefficient of $x$: ${tex(line_slope)}$."
    )
    neg_recip = (
        f"Perpendicular slopes multiply to $-1$, so the slope of $p$ is the negative reciprocal "
        f"of ${tex(line_slope)}$: ${tex(perp)}$."
    )
    if d == "medium":
        key = perp
        stem = f"Line $\\ell$ is defined by ${eq}$. Line $p$ is perpendicular to line $\\ell$. What is the slope of line $p$?"
        dist = ds(
            (
                lambda: line_slope,
                "concept",
                "That's the slope of line $\\ell$ (parallel, not perpendicular).",
            ),
            (lambda: -perp, "sign_flip", "Took the reciprocal but forgot to change the sign."),
            (lambda: -line_slope, "partial_solution", "Changed the sign but forgot to take the reciprocal."),
            (lambda: R(a, b), "sign_flip", "Read the slope off as $a/b$; solving for $y$ gives $-a/b$."),
        )
        steps = [solve_y, neg_recip]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key * line_slope == -1,
        )
    p_, q_ = ri(rng, -6, 6), ri(rng, -9, 9)
    key = q_ - perp * p_
    stem = (
        f"Line $\\ell$ is defined by ${eq}$. Line $p$ is perpendicular to line $\\ell$ and passes "
        f"through the point {pt(p_, q_)}. What is the $y$-coordinate of the $y$-intercept of line $p$?"
    )
    dist = ds(
        (
            lambda: q_ - line_slope * p_,
            "concept",
            "Used the slope of $\\ell$ itself (that gives a parallel line).",
        ),
        (lambda: q_ + perp * p_, "sign_flip", "Sign error: $b = y - mx$."),
        (lambda: perp, "misread", "That's the slope of line $p$."),
        (lambda: R(c, b), "misread", "That's the $y$-intercept of line $\\ell$."),
    )
    steps = [
        solve_y,
        neg_recip,
        f"Write $p$ as $y = {tex(perp)}x + b$ and plug in {pt(p_, q_)}: ${q_} = ({tex(perp)})({p_}) + b$.",
        f"$b = {q_} - ({tex(perp)})({p_}) = {tex(key)}$, so the $y$-intercept is ${tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(perp * p_ + key, q_, {}) and holds(perp * line_slope, -1, {}),
    )


LINF_CTX = [
    (
        "A candle is {h} centimeters tall and burns down {r} centimeters per hour.",
        "H(t)",
        "height, in centimeters, after $t$ hours",
    ),
    (
        "A water tank holds {h} liters and drains at {r} liters per minute.",
        "W(t)",
        "amount of water, in liters, after $t$ minutes",
    ),
    (
        "A phone battery is at {h} percent and loses {r} percentage points per hour of use.",
        "B(t)",
        "battery level, in percent, after $t$ hours",
    ),
]


@register(S + "LINF.MODEL")
def linf_model(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LINF.MODEL"
    if d == "easy":
        desc, fn, what = rng.choice(LINF_CTX)
        h, r = ri(rng, 20, 100), ri(rng, 2, 9)
        t = sympy.Symbol("t")
        expr = h - r * t
        key = f"${fn} = {h} - {r}t$"
        stem = desc.format(h=h, r=r) + f" Which function gives the {what}?"
        dist = [
            D(f"${fn} = {h} + {r}t$", "sign_flip", "The quantity decreases, so the rate is subtracted."),
            D(f"${fn} = {r} - {h}t$", "misread", "Swapped the starting value and the rate."),
            D(f"${fn} = ({h} - {r})t$", "distribution", "This multiplies the starting value by $t$."),
            D(f"${fn} = {h}t - {r}$", "misread", "Swapped which number goes with $t$."),
        ]
        steps = [f"Start at ${h}$ and subtract ${r}$ for each unit of time: {key}."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: expr.subs(t, 2) == h - r - r,
        )
    slope = R(ri(rng, 2, 9), rng.choice([1, 1, 2]))
    t1 = ri(rng, 1, 4)
    t2 = t1 + ri(rng, 2, 5)
    v0 = ri(rng, 10, 30)
    v1, v2 = v0 + slope * t1, v0 + slope * t2
    s_, c_ = sympy.symbols("s c")
    sol = sympy.solve([sympy.Eq(s_ * t1 + c_, v1), sympy.Eq(s_ * t2 + c_, v2)], [s_, c_])
    if d == "medium":
        t3 = t2 + ri(rng, 2, 6)
        key = sol[s_] * t3 + sol[c_]
        stem = (
            f"The temperature of a liquid rises at a constant rate. After {t1} minutes it is "
            f"${tex(v1)}^\\circ\\text{{C}}$, and after {t2} minutes it is ${tex(v2)}^\\circ\\text{{C}}$. What is "
            f"the temperature, in degrees Celsius, after {t3} minutes?"
        )
        dist = ds(
            (
                lambda: v2 + (v2 - v1),
                "wrong_formula",
                f"Added the same change again, but {t3 - t2} minutes ≠ {t2 - t1} minutes.",
            ),
            (lambda: sol[s_] * t3, "wrong_formula", "Left out the starting temperature."),
            (
                lambda: v2 - sol[s_] * (t3 - t2),
                "sign_flip",
                "The temperature is rising, so the change is added.",
            ),
            (lambda: sol[s_], "partial_solution", "That's the rate per minute."),
        )
        steps = [
            f"Rate: $\\frac{{{tex(v2)} - {tex(v1)}}}{{{t2 - t1}}} = {tex(sol[s_])}$ per minute.",
            f"After {t3} minutes: ${tex(v2)} + {tex(sol[s_])}({t3 - t2}) = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(v0 + slope * t3, key, {}),
        )
    target = v2 + slope * ri(rng, 3, 9)
    key = sympy.solve(sympy.Eq(sol[s_] * x + sol[c_], target), x)[0]
    stem = (
        f"The temperature of a liquid rises at a constant rate. After {t1} minutes it is "
        f"${tex(v1)}^\\circ\\text{{C}}$, and after {t2} minutes it is ${tex(v2)}^\\circ\\text{{C}}$. After how "
        f"many minutes will the temperature be ${tex(target)}^\\circ\\text{{C}}$?"
    )
    dist = ds(
        (
            lambda: (target - v2) / sol[s_],
            "partial_solution",
            f"That's the time after minute {t2}, not since the start.",
        ),
        (lambda: target / sol[s_], "wrong_formula", "Ignored the starting temperature."),
        (lambda: (target - v1) / sol[s_] + t2, "misread", "Mixed up which reading to count from."),
        (
            lambda: (target - sol[c_]) * sol[s_],
            "operation_swap",
            "Multiplied by the rate instead of dividing.",
        ),
    )
    steps = [
        f"Rate: ${tex(sol[s_])}$ °C per minute; starting temperature $f(0) = {tex(sol[c_])}$.",
        f"Solve ${tex(sol[c_])} + {tex(sol[s_])}t = {tex(target)}$: $t = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(v0 + slope * key, target, {}),
    )


# ---------- SYS: systems of linear equations ----------


@register(S + "SYS.SOLVE")
def sys_solve(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "SYS.SOLVE"
    x0, y0 = ri(rng, -6, 9), ri(rng, -6, 9)
    if d == "easy":
        a, b = ri(rng, -4, 5), ri(rng, -9, 9)
        c = ri(rng, 1, 5, (0, -a))
        e = c * x0 + (a * x0 + b)
        y0 = a * x0 + b
        eqs = (sympy.Eq(y, a * x + b), sympy.Eq(c * x + y, e))
        key = sympy.solve(eqs, [x, y])[x]
        dist = ds(
            (lambda: R(y0), "misread", "That's the value of $y$."),
            (lambda: R(e + b, c + a), "sign_flip", "Sign error when substituting and moving the constant."),
            (lambda: R(e - b, c - a), "sign_flip", "Subtracted the $x$-terms instead of adding them."),
            (
                lambda: R(e - b, c),
                "partial_solution",
                "Dropped the $x$-term that came from substituting $y$.",
            ),
        )
        stem = f"$$y = {lin(a, b)}$$ $${lin(c, 0)} + y = {e}$$ If $(x, y)$ is the solution to the system above, what is the value of $x$?"
        steps = [f"Substitute: ${c}x + ({lin(a, b)}) = {e}$.", f"${c + a}x = {e - b}$, so $x = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(c * key + a * key + b, e, {}),
        )
    while True:
        a1, b1, a2, b2 = (ri(rng, -6, 7) for _ in range(4))
        if a1 * b2 - a2 * b1 != 0:
            break
    if d == "hard":
        x0, y0 = R(ri(rng, -9, 9), rng.choice([2, 3])), R(ri(rng, -9, 9), rng.choice([1, 2]))
    c1, c2 = a1 * x0 + b1 * y0, a2 * x0 + b2 * y0
    sol = sympy.solve([sympy.Eq(a1 * x + b1 * y, c1), sympy.Eq(a2 * x + b2 * y, c2)], [x, y])
    sys_tex = f"$${lin(a1, 0)} + {lin(b1, 0, 'y')} = {tex(c1)}$$ $${lin(a2, 0)} + {lin(b2, 0, 'y')} = {tex(c2)}$$".replace(
        "+ -", "- "
    )
    if d == "medium":
        key = sol[y]
        stem = sys_tex + " If $(x, y)$ is the solution to the system above, what is the value of $y$?"
        dist = ds(
            (lambda: sol[x], "misread", "That's the value of $x$."),
            (lambda: -sol[y], "sign_flip", "Sign error during elimination."),
            (lambda: sol[x] + sol[y], "misread", "That's $x + y$."),
            (lambda: R(c1 + c2, b1 + b2), "partial_solution", "Added the equations without eliminating $x$."),
        )
        steps = [
            "Eliminate $x$: multiply the equations so the $x$-coefficients cancel, then subtract.",
            f"$y = {tex(key)}$ (and $x = {tex(sol[x])}$).",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(a1 * x0 + b1 * key, c1, {}) and holds(a2 * x0 + b2 * key, c2, {}),
        )
    p_, q_ = ri(rng, 2, 5), ri(rng, -4, 4)
    key = p_ * sol[x] + q_ * sol[y]
    stem = (
        sys_tex
        + f" If $(x, y)$ is the solution to the system above, what is the value of ${lin(p_, 0)} + {lin(q_, 0, 'y')}$?".replace(
            "+ -", "- "
        )
    )
    dist = ds(
        (lambda: p_ * sol[x] - q_ * sol[y], "sign_flip", "Sign error on the $y$-term."),
        (lambda: sol[x] + sol[y], "misread", "That's $x + y$."),
        (lambda: p_ * sol[x], "partial_solution", "Left out the $y$-term."),
        (lambda: p_ * sol[y] + q_ * sol[x], "misread", "Swapped $x$ and $y$."),
    )
    steps = [
        f"Solve the system: $x = {tex(sol[x])}$, $y = {tex(sol[y])}$.",
        f"${p_}({tex(sol[x])}) + ({q_})({tex(sol[y])}) = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(p_ * x0 + q_ * y0, key, {}),
    )


@register(S + "SYS.NSOL")
def sys_nsol(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "SYS.NSOL"
    key: Value
    if d == "easy":
        mv, b1 = ri(rng, -5, 5), ri(rng, -9, 9)
        case = rng.choice(["zero", "one", "inf"])
        m2 = mv if case != "one" else mv + ri(rng, 1, 3)
        t = ri(rng, 2, 4)
        b2 = b1 if case != "zero" else b1 + ri(rng, 1, 6)
        # second line written in a scaled standard form so "same line" isn't obvious
        eq2 = f"{t}y = {lin(t * m2, t * b2)}"
        sols = sympy.solve(
            [sympy.Eq(y, mv * x + b1), sympy.Eq(t * y, t * m2 * x + t * b2)], [x, y], dict=True
        )
        found = (
            "zero" if not sols else ("one" if not sols[0].keys() - {x, y} and len(sols[0]) == 2 else "inf")
        )
        key = NSOL_CHOICES[found]
        stem = f"$$y = {lin(mv, b1)}$$ $${eq2}$$ How many solutions does the system of equations above have?"
        steps = [
            f"Divide the second equation by ${t}$: $y = {lin(m2, b2)}$.",
            {
                "zero": "Same slope, different intercepts: parallel lines, no solution.",
                "one": "Different slopes: the lines cross once.",
                "inf": "Same slope and intercept: the same line, infinitely many solutions.",
            }[found],
        ]

        def verify() -> bool:
            if case == "one":
                return m2 != mv
            return m2 == mv and ((b1 == b2) == (case == "inf"))

        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=_nsol_choices(found),
            steps=steps,
            verify=verify,
        )
    a, b, c = ri(rng, -6, 6), ri(rng, 2, 7), ri(rng, -12, 12)
    t = rng.choice([2, 3, 4, R(1, 2), R(3, 2)])
    if d == "medium":
        dv, e = t * b, t * c + ri(rng, 1, 8)
        key = sympy.solve(sympy.Eq(k * b - a * dv, 0), k)[0]
        stem = (
            f"$${lin(a, 0)} + {b}y = {c}$$ $$kx + {tex(dv)}y = {tex(e)}$$ In the system above, $k$ is a "
            "constant. For what value of $k$ does the system have no solution?"
        ).replace("+ -", "- ")
        dist = ds(
            (
                lambda: R(a),
                "partial_solution",
                f"Didn't scale by the factor ${tex(t)}$ between the equations.",
            ),
            (lambda: -key, "sign_flip", "Sign error: the coefficients must be in the same ratio."),
            (lambda: R(b) * t / a if a else None, "reciprocal", "Set up the ratio upside down."),
            (lambda: R(c) * t, "concept", "Scaled the constant instead of the $x$-coefficient."),
        )
        steps = [
            "No solution means parallel lines: the $x$- and $y$-coefficients are in the same ratio, but the constants aren't.",
            f"$\\frac{{k}}{{{a}}} = \\frac{{{tex(dv)}}}{{{b}}}$, so $k = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(key * b, a * dv, {}) and not holds(c * t, e, {}),
        )
    kv, rv = a * t, c * t
    r_ = sympy.Symbol("r")
    sol = sympy.solve([sympy.Eq(k * b, a * t * b), sympy.Eq(r_ * b, c * t * b)], [k, r_])
    key = sol[k] + sol[r_]
    stem = (
        f"$${lin(a, 0)} + {b}y = {c}$$ $$kx + {tex(t * b)}y = r$$ In the system above, $k$ and $r$ are "
        "constants. If the system has infinitely many solutions, what is the value of $k + r$?"
    ).replace("+ -", "- ")
    dist = ds(
        (lambda: R(a + c), "partial_solution", f"Didn't scale by the factor ${tex(t)}$."),
        (lambda: sol[k], "misread", "That's only $k$."),
        (lambda: sol[k] - sol[r_], "sign_flip", "Computed $k - r$."),
        (lambda: sol[r_], "misread", "That's only $r$."),
    )
    steps = [
        f"Infinitely many solutions: the second equation is ${tex(t)}$ times the first.",
        f"$k = {tex(kv)}$, $r = {tex(rv)}$, so $k + r = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(sol[k] * b, a * t * b, {}) and holds(sol[r_], c * t, {}),
    )


@register(S + "SYS.MODEL")
def sys_model(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "SYS.MODEL"
    pp, pn = rng.sample(range(2, 9), 2)
    np_, nn = rng.sample(range(3, 16), 2)
    n_tot, t_tot = np_ + nn, pp * np_ + pn * nn
    if d == "easy":
        sol = sympy.solve([sympy.Eq(x + y, n_tot), sympy.Eq(pp * x + pn * y, t_tot)], [x, y])
        key = sol[y]
        stem = (
            f"A store sells pens for \\${pp} each and notebooks for \\${pn} each. A customer bought {n_tot} "
            f"items for a total of \\${t_tot}. How many notebooks did the customer buy?"
        )
        dist = ds(
            (lambda: sol[x], "misread", "That's the number of pens."),
            (
                lambda: sympy.solve([sympy.Eq(x + y, n_tot), sympy.Eq(pn * x + pp * y, t_tot)], [x, y])[y],
                "misread",
                "Swapped the prices.",
            ),
            (lambda: R(t_tot, pp + pn), "wrong_formula", "Divided the total by the sum of the prices."),
            (lambda: R(n_tot, 2), "concept", "Assumed equal numbers of each item."),
        )
        steps = [
            f"$p + n = {n_tot}$ and ${pp}p + {pn}n = {t_tot}$.",
            f"Substitute $p = {n_tot} - n$: $n = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: pp * (n_tot - key) + pn * key == t_tot,
        )
    if d == "medium":
        key = f"$x + y = {n_tot}$ and ${pp}x + {pn}y = {t_tot}$"
        stem = (
            f"A store sells pens for \\${pp} each and notebooks for \\${pn} each. A customer bought {n_tot} "
            f"items for \\${t_tot}: $x$ pens and $y$ notebooks. Which system of equations represents this situation?"
        )
        dist = [
            D(
                f"$x + y = {t_tot}$ and ${pp}x + {pn}y = {n_tot}$",
                "misread",
                "Swapped the item count and the cost.",
            ),
            D(
                f"$x + y = {n_tot}$ and ${pn}x + {pp}y = {t_tot}$",
                "misread",
                "The prices are on the wrong variables.",
            ),
            D(
                f"$x + y = {n_tot}$ and ${pp + pn}(x + y) = {t_tot}$",
                "wrong_formula",
                "Charges each item both prices.",
            ),
            D(
                f"${pp}x = {pn}y$ and $x + y = {n_tot}$",
                "concept",
                "Nothing says the two amounts spent are equal.",
            ),
        ]
        steps = ["Count of items: $x + y$. Money: price times quantity for each, added."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: np_ + nn == n_tot and pp * np_ + pn * nn == t_tot,
        )
    a, b = rng.sample([10, 15, 20, 25, 30, 40, 50, 60], 2)
    a, b = min(a, b), max(a, b)
    while True:
        u, w = ri(rng, 2, 12) * 5, ri(rng, 2, 12) * 5
        if (a * u + b * w) % (u + w) == 0:
            break
    v, c = u + w, (a * u + b * w) // (u + w)
    sol = sympy.solve([sympy.Eq(x + y, v), sympy.Eq(R(a, 100) * x + R(b, 100) * y, R(c, 100) * v)], [x, y])
    key = sol[x]
    stem = (
        f"A chemist mixes a {a}% acid solution with a {b}% acid solution to make {v} liters of a {c}% acid "
        f"solution. How many liters of the {a}% solution are used?"
    )
    dist = ds(
        (lambda: sol[y], "misread", f"That's the amount of the {b}% solution."),
        (
            lambda: R(v, 2),
            "concept",
            "Equal amounts only give a mixture halfway between the two concentrations.",
        ),
        (lambda: R(c * v, b), "wrong_formula", "Accounted for acid from only one solution."),
        (lambda: R(v * (c - a), b), "wrong_formula", "Set up the balance with the wrong differences."),
    )
    steps = [
        f"$x + y = {v}$ and $0.{a:02d}x + 0.{b:02d}y = 0.{c:02d}({v})$." if b < 100 else "",
        f"Solve: $x = {tex(key)}$ liters of the {a}% solution.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=[s_ for s_ in steps if s_],
        verify=lambda: a * key + b * (v - key) == c * v,
    )


# ---------- INEQ: linear inequalities ----------

OPS = {"<": "<", "<=": "\\le", ">": ">", ">=": "\\ge"}
FLIP = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}


def _rel(op: str, lhs: sympy.Expr, rhs: sympy.Expr) -> sympy.Basic:
    return {"<": sympy.Lt, "<=": sympy.Le, ">": sympy.Gt, ">=": sympy.Ge}[op](lhs, rhs)


@register(S + "INEQ.SOLVE")
def ineq_solve(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "INEQ.SOLVE"
    op = rng.choice(list(OPS))
    if d in ("easy", "medium"):
        a = ri(rng, 2, 8) * (1 if d == "easy" else -1)
        b, bound = ri(rng, -12, 12), ri(rng, -8, 9)
        c = a * bound + b
        lhs = a * x + b
        bnd = sympy.solve(sympy.Eq(lhs, c), x)[0]
        res_op = op if a > 0 else FLIP[op]

        def show(o: str, v: sympy.Basic) -> str:
            return f"$x {OPS[o]} {tex(v)}$"

        key = show(res_op, bnd)
        dist = ds(
            (
                lambda: show(FLIP[res_op], bnd),
                "concept",
                "Reversed the inequality incorrectly."
                if a > 0
                else "Correct boundary, but the direction must flip when dividing by a negative.",
            ),
            (lambda: show(res_op, R(c + b, a)), "sign_flip", "Sign error when moving the constant."),
            (lambda: show(res_op, R(c - b)), "partial_solution", f"Forgot to divide by ${a}$."),
            (
                lambda: show(op if a < 0 else FLIP[op], R(c + b, a)),
                "sign_flip",
                "Sign error and wrong direction.",
            ),
        )
        stem = f"Which inequality is equivalent to ${tex(lhs)} {OPS[op]} {c}$?"
        steps = [
            f"Subtract ${b}$: ${a}x {OPS[op]} {c - b}$.",
            f"Divide by ${a}$" + (" and flip the sign" if a < 0 else "") + f": {key}.",
        ]

        def verify() -> bool:
            inside = bnd + (R(1, 2) if res_op in (">", ">=") else -R(1, 2))
            return bool(_rel(op, lhs.subs(x, inside), c)) and not bool(
                _rel(op, lhs.subs(x, 2 * bnd - inside), c)
            )

        return build(rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps, verify=verify)
    p_, s_ = rng.sample([2, 3, 4, 5, 6], 2)
    q_, r_ = ri(rng, 1, 6), ri(rng, -6, 6)
    lhs, rhs = x / p_ - q_, (x + r_) / s_
    # Direction chosen so the solution set is bounded above: x < bound.
    ineq = sympy.Gt(lhs, rhs) if p_ > s_ else sympy.Lt(lhs, rhs)
    sol_set = sympy.solve_univariate_inequality(ineq, x, relational=False)
    sup = sol_set.sup
    key = sympy.floor(sup) - (1 if sup.is_integer and sol_set.right_open else 0)
    sym = ">" if p_ > s_ else "<"
    stem = (
        f"$$\\frac{{x}}{{{p_}}} - {q_} {sym} \\frac{{x {'+' if r_ >= 0 else '-'} {abs(r_)}}}{{{s_}}}$$ "
        "What is the greatest integer that satisfies the inequality above?"
    )
    dist = ds(
        (lambda: key + 1, "off_by_one", "This value makes the inequality false (check the boundary)."),
        (
            lambda: sympy.ceiling(sup) if not sup.is_integer else sup + 1,
            "off_by_one",
            "Rounded the boundary the wrong way.",
        ),
        (lambda: -key, "sign_flip", "Sign error while clearing fractions."),
        (lambda: key - 1, "off_by_one", "A smaller integer also works, but it isn't the greatest."),
        (lambda: sup, "misread", "That's the boundary of the solution set, not the greatest integer in it."),
        (lambda: -sympy.floor(sup) - 1, "sign_flip", "Sign error while clearing fractions."),
    )
    steps = [
        f"Multiply by ${p_ * s_}$ and collect $x$-terms; the solution set is $x < {tex(sup)}$.",
        f"The greatest integer below ${tex(sup)}$ is ${tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: bool(ineq.subs(x, key)) and not bool(ineq.subs(x, key + 1)),
    )


@register(S + "INEQ.GRAPH")
def ineq_graph(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "INEQ.GRAPH"
    m1, b1 = R(ri(rng, -4, 4), rng.choice([1, 2])), ri(rng, -6, 6)
    m2, b2 = R(ri(rng, -4, 4), rng.choice([1, 2])), b1 + ri(rng, 3, 8)  # (0, b1 + 1) is always a solution
    while m2 == m1:
        m2 = R(ri(rng, -4, 4), 1)
    i1 = sympy.Gt(y, m1 * x + b1)
    i2 = sympy.Le(y, m2 * x + b2)

    def ok(rel: sympy.Basic, px: sympy.Basic, py: sympy.Basic) -> bool:
        return bool(rel.subs({x: px, y: py}))

    def stem_ineq(rel: sympy.Basic) -> str:
        return str(sympy.latex(rel))

    if d == "hard":
        x0 = ri(rng, -4, 4)
        lo, hi = m1 * x0 + b1, m2 * x0 + b2
        while hi - lo < 2:
            x0 += 1 if m2 > m1 else -1
            lo, hi = m1 * x0 + b1, m2 * x0 + b2
        key = sympy.floor(hi)
        stem = (
            f"$${stem_ineq(i1)}$$ $${stem_ineq(i2)}$$ The point $({x0}, k)$ is a solution to the system of "
            "inequalities above. What is the greatest possible integer value of $k$?"
        )
        dist = ds(
            (lambda: key + 1, "off_by_one", "This point lies above the boundary line $y \\le \\dots$"),
            (lambda: sympy.floor(lo) + 1, "misread", "That's the least possible integer value."),
            (lambda: sympy.floor(m2 * -x0 + b2), "sign_flip", "Substituted the wrong sign of $x$."),
            (
                lambda: sympy.ceiling(hi) + 1 if hi.is_integer else sympy.ceiling(hi),
                "off_by_one",
                "Rounded the upper bound up.",
            ),
        )
        steps = [f"At $x = {x0}$: ${tex(lo)} < k \\le {tex(hi)}$.", f"Greatest integer $k$: ${tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: ok(i1, x0, key) and ok(i2, x0, key) and not ok(i2, x0, key + 1),
        )
    rels = [i1] if d == "easy" else [i1, i2]
    pts = [(px, py) for px in range(-5, 6) for py in range(-8, 9)]
    rng.shuffle(pts)
    good = [p for p in pts if all(ok(r, *p) for r in rels)]
    bad = [p for p in pts if not all(ok(r, *p) for r in rels)]
    kx, ky = good[0]
    key = pt(kx, ky)
    cands: list[D] = []
    for px, py in bad[:8]:
        if d == "medium" and ok(i1, px, py):
            why, model = "Satisfies the first inequality but not the second.", "partial_solution"
        elif d == "medium" and ok(i2, px, py):
            why, model = "Satisfies the second inequality but not the first.", "partial_solution"
        elif py == m1 * px + b1:
            why, model = "On the boundary line, but the inequality is strict.", "off_by_one"
        else:
            why, model = "Substituting this point makes an inequality false.", "sign_flip"
        cands.append(D(pt(px, py), model, why))
    stem = "".join(f"$${stem_ineq(r)}$$ " for r in rels) + (
        "Which point $(x, y)$ is a solution to the inequality above?"
        if d == "easy"
        else "Which point $(x, y)$ is a solution to the system of inequalities above?"
    )
    steps = [
        f"Substitute each point. {key} makes every inequality true; each other choice fails at least one."
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=cands,
        steps=steps,
        verify=lambda: all(ok(r, kx, ky) for r in rels),
    )


@register(S + "INEQ.MODEL")
def ineq_model(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "INEQ.MODEL"
    key: Value
    w_max, drv, box = ri(rng, 15, 40) * 100, ri(rng, 60, 110), ri(rng, 15, 60)
    if d == "easy":
        n = sympy.Symbol("n")
        key = f"${drv} + {box}n \\le {w_max}$"
        stem = (
            f"An elevator can carry at most {w_max} kilograms. A worker who weighs {drv} kilograms rides with "
            f"$n$ boxes that weigh {box} kilograms each. Which inequality represents this situation?"
        )
        dist = [
            D(f"${drv} + {box}n \\ge {w_max}$", "concept", "'At most' means less than or equal to."),
            D(
                f"${box}n \\le {w_max} + {drv}$",
                "sign_flip",
                "The worker's weight uses up capacity; it isn't added to it.",
            ),
            D(
                f"${box}({drv} + n) \\le {w_max}$",
                "distribution",
                "This multiplies the worker's weight by the box weight.",
            ),
            D(f"${drv}n + {box} \\le {w_max}$", "misread", "Swapped the worker's weight and the box weight."),
        ]
        steps = [f"Total weight is ${drv} + {box}n$, and it must be at most ${w_max}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: bool(sympy.Le(drv + box * n, w_max).subs(n, 0)),
        )
    if d == "medium":
        sol = sympy.solve_univariate_inequality(sympy.Le(drv + box * x, w_max), x, relational=False)
        key = sympy.floor(sol.sup)
        stem = (
            f"An elevator can carry at most {w_max} kilograms. A worker who weighs {drv} kilograms rides with "
            f"boxes that weigh {box} kilograms each. What is the greatest number of boxes the worker can take?"
        )
        dist = ds(
            (lambda: sympy.floor(R(w_max, box)), "misread", "Forgot to subtract the worker's weight."),
            (lambda: key + 1, "off_by_one", "Rounded up: that many boxes exceeds the limit."),
            (
                lambda: sympy.floor(R(w_max + drv, box)),
                "sign_flip",
                "Added the worker's weight to the capacity.",
            ),
            (lambda: R(w_max - drv), "partial_solution", "That's the remaining capacity in kilograms."),
        )
        steps = [
            f"${drv} + {box}n \\le {w_max}$ gives $n \\le {tex(R(w_max - drv, box))}$.",
            f"Greatest whole number: ${tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: drv + box * key <= w_max < drv + box * (key + 1),
        )
    s_, h_ = ri(rng, 8, 25), ri(rng, 5, 18)
    extra = ri(rng, 2, 5)
    budget = ri(rng, 15, 40) * 10
    sol = sympy.solve_univariate_inequality(sympy.Le(s_ * x + h_ * (x + extra), budget), x, relational=False)
    key = sympy.floor(sol.sup)
    stem = (
        f"Maya can spend at most \\${budget} on shirts that cost \\${s_} each and hats that cost \\${h_} each. "
        f"She wants to buy {extra} more hats than shirts. What is the greatest number of shirts she can buy?"
    )
    dist = ds(
        (lambda: sympy.floor(R(budget, s_ + h_)), "partial_solution", f"Ignored the {extra} extra hats."),
        (lambda: key + 1, "off_by_one", "Rounded up: that exceeds the budget."),
        (
            lambda: sympy.floor(R(budget + extra * h_, s_ + h_)),
            "sign_flip",
            "Added the cost of the extra hats to the budget.",
        ),
        (lambda: key + extra, "misread", "That's the number of hats."),
    )
    steps = [
        f"${s_}x + {h_}(x + {extra}) \\le {budget}$, so ${s_ + h_}x \\le {budget - extra * h_}$.",
        f"$x \\le {tex(R(budget - extra * h_, s_ + h_))}$; greatest whole number: ${tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: s_ * key + h_ * (key + extra) <= budget < s_ * (key + 1) + h_ * (key + 1 + extra),
    )
