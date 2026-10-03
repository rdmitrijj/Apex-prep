"""Advanced Math generators (MATH.ADV.*)."""

import random
from collections.abc import Callable

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
    pt,
    register,
    ri,
    tex,
    x,
)

S = "MATH.ADV."
xp = sympy.Symbol("x", positive=True)


def _eq_fmt(lhs: str) -> Callable[[Value], str]:
    def fmt(v: Value) -> str:
        return f"${lhs} = {tex(v)}$"

    return fmt


# ---------- EQX: equivalent expressions ----------


@register(S + "EQX.POLY")
def eqx_poly(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "EQX.POLY"
    a, c = ri(rng, 1, 5), ri(rng, 1, 5)
    b, e = ri(rng, -9, 9), ri(rng, -9, 9)
    if d == "easy":
        expr = (a * x + b) * (c * x + e)
        key = sympy.expand(expr)
        stem = f"Which expression is equivalent to $({lin(a, b)})({lin(c, e)})$?"
        dist = ds(
            (
                lambda: a * c * x**2 + b * e,
                "distribution",
                "Multiplied only first terms and last terms; the middle terms are missing.",
            ),
            (
                lambda: a * c * x**2 + (a * e + b * c) * x - b * e,
                "sign_flip",
                "Sign error on the constant term.",
            ),
            (
                lambda: a * c * x**2 + a * e * x + b * e,
                "partial_solution",
                "Missed one of the two middle products.",
            ),
            (
                lambda: a * c * x**2 + (a * e - b * c) * x + b * e,
                "sign_flip",
                "Sign error on one middle product.",
            ),
            (lambda: (a + c) * x + b + e, "operation_swap", "Added the factors instead of multiplying."),
        )
        steps = [
            f"Multiply every term: ${a * c}x^2 + {a * e}x + {b * c}x + {b * e}$.",
            f"Combine: ${tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: (
                holds(expr, key, {x: 3}) and holds(expr, key, {x: -2}) and holds(expr, key, {x: 5})
            ),
        )
    if d == "medium":
        p_, r_ = rng.choice([(2, 3), (3, 2), (2, 1), (1, 3), (3, 4), (4, 3), (2, 5), (6, 1)])
        q_, s_ = ri(rng, -7, 7), ri(rng, -7, 7)
        while sympy.gcd(p_, q_) != 1 or sympy.gcd(r_, s_) != 1 or p_ * s_ == r_ * q_:
            q_, s_ = ri(rng, -7, 7), ri(rng, -7, 7)
        poly = sympy.expand((p_ * x + q_) * (r_ * x + s_))
        key = p_ * x + q_
        cands = [
            (p_ * x - q_, "sign_flip", "Sign error: check by multiplying back out."),
            (q_ * x + p_, "misread", "Swapped the coefficient and the constant."),
            (r_ * x - s_, "sign_flip", "Sign error in the other factor."),
            (x + q_ * p_, "concept", "Not a factor: it doesn't divide evenly."),
            (p_ * x + s_, "misread", "Mixed the constant from one factor with the other."),
        ]
        dist = [D(v, mo, why) for v, mo, why in cands if sympy.rem(poly, v, x) != 0]
        stem = f"Which of the following is a factor of ${tex(poly)}$?"
        steps = [f"${tex(poly)} = ({lin(p_, q_)})({lin(r_, s_)})$.", f"So ${lin(p_, q_)}$ is a factor."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: sympy.rem(poly, key, x) == 0,
        )
    b_ = sympy.Symbol("b")
    while b == 0 or e == 0:
        b, e = ri(rng, -9, 9), ri(rng, -9, 9)
    target = sympy.expand((a * x + b) * (c * x + e))
    const = target.subs(x, 0)
    sol = sympy.solve(sympy.Eq(b * b_, const), b_)[0]
    key = sympy.expand((a * x + b) * (c * x + sol)).coeff(x, 1)
    stem = (
        f"$$({lin(a, b)})({c if c != 1 else ''}x + b) = {tex(a * c * x**2)} + kx {'+' if const >= 0 else '-'} {abs(const)}$$ "
        "In the equation above, $b$ and $k$ are constants. If the equation is true for all values of $x$, "
        "what is the value of $k$?"
    )
    dist = ds(
        (lambda: a * sol - b * c, "sign_flip", "Sign error when adding the middle products."),
        (lambda: sol + b, "distribution", "Forgot to multiply by the $x$-coefficients."),
        (lambda: sol, "misread", "That's the value of $b$."),
        (lambda: a * c, "misread", "That's the coefficient of $x^2$."),
    )
    steps = [
        f"Constant terms: ${b}b = {const}$, so $b = {tex(sol)}$.",
        f"$x$-terms: $k = {a}({tex(sol)}) + ({b})({c}) = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: sympy.expand((a * x + b) * (c * x + sol) - (a * c * x**2 + key * x + const)) == 0,
    )


@register(S + "EQX.EXP")
def eqx_exp(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "EQX.EXP"
    if d == "easy":
        a, b = ri(rng, 2, 9), ri(rng, 2, 9)
        c = ri(rng, 2, 5)
        expr = c * xp**a * xp**b
        key = c * xp ** (a + b)
        stem = f"Which expression is equivalent to $({c}x^{{{a}}})(x^{{{b}}})$?"
        dist = ds(
            (
                lambda: c * xp ** (a * b),
                "exponent_rule",
                "Multiplied the exponents; when multiplying powers, add them.",
            ),
            (
                lambda: c * xp ** abs(a - b) if a != b else c * xp,
                "exponent_rule",
                "Subtracted the exponents.",
            ),
            (
                lambda: f"$({c}x)^{{{a + b}}}$",
                "exponent_rule",
                f"The exponent applies to $x$ only, not to ${c}$.",
            ),
            (lambda: c * xp ** (a + b + 1), "off_by_one", "Arithmetic slip adding the exponents."),
        )
        steps = [f"Add exponents: $x^{{{a}}} \\cdot x^{{{b}}} = x^{{{a + b}}}$.", f"So ${tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(expr, key, {xp: 2}) and holds(expr, key, {xp: 3}),
        )
    if d == "medium":
        n_ = rng.choice([2, 3, 4, 5])
        m_ = ri(rng, 1, 7)
        while sympy.gcd(m_, n_) != 1:
            m_ = ri(rng, 1, 7)
        b = ri(rng, 1, 4)
        expr = sympy.root(xp**m_, n_) * xp**b
        key = xp ** (R(m_, n_) + b)
        rad = "x" if m_ == 1 else f"x^{{{m_}}}"
        root_tex = f"\\sqrt{{{rad}}}" if n_ == 2 else f"\\sqrt[{n_}]{{{rad}}}"
        stem = f"For $x > 0$, which expression is equivalent to ${root_tex} \\cdot {'x' if b == 1 else f'x^{{{b}}}'}$?"
        dist = ds(
            (
                lambda: xp ** (R(n_, m_) + b),
                "reciprocal",
                "Inverted the fractional exponent: the root index goes in the denominator.",
            ),
            (lambda: xp ** (R(m_, n_) * b), "exponent_rule", "Multiplied the exponents instead of adding."),
            (
                lambda: xp ** (m_ * n_ + b),
                "exponent_rule",
                "A root divides the exponent; it doesn't multiply it.",
            ),
            (lambda: xp ** R(m_ + b, n_), "partial_solution", "Put the extra factor under the root too."),
        )
        steps = [f"${root_tex} = x^{{{m_}/{n_}}}$.", f"Add exponents: $x^{{{tex(R(m_, n_) + b)}}}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: abs(sympy.N(expr.subs(xp, 7) - key.subs(xp, 7))) < 1e-9,
        )
    base = rng.choice([2, 3])
    a, b, c = ri(rng, 1, 4), ri(rng, -5, 5), ri(rng, 1, 6)
    lhs = base ** (a * x) * (base**2) ** (x + b)
    rhs = (base**3) ** c
    key = sympy.solve(sympy.Eq(a * x + 2 * (x + b), 3 * c), x)[0]
    stem = (
        f"$${base}^{{{a if a != 1 else ''}x}} \\cdot {base**2}^{{x {'+' if b >= 0 else '-'} {abs(b)}}} = {base**3}^{{{c}}}$$ "
        "What value of $x$ satisfies the equation above?"
    )
    dist = ds(
        (
            lambda: sympy.solve(sympy.Eq(a * x + x + b, 3 * c), x)[0],
            "exponent_rule",
            f"Didn't rewrite ${base**2}$ as ${base}^2$.",
        ),
        (
            lambda: sympy.solve(sympy.Eq(a * x + 2 * x + b, 3 * c), x)[0],
            "distribution",
            "Multiplied only $x$ by 2, not the constant.",
        ),
        (
            lambda: sympy.solve(sympy.Eq(a * x + 2 * (x + b), c), x)[0],
            "exponent_rule",
            f"Didn't rewrite ${base**3}$ as ${base}^3$.",
        ),
        (lambda: key + 1, "off_by_one", "Arithmetic slip solving the exponent equation."),
    )
    steps = [
        f"Rewrite with base ${base}$: ${base}^{{{a}x}} \\cdot {base}^{{2x + {2 * b}}} = {base}^{{{3 * c}}}$.".replace(
            "+ -", "- "
        ),
        f"Equate exponents: ${a}x + 2x + {2 * b} = {3 * c}$, so $x = {tex(key)}$.".replace("+ -", "- "),
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(lhs, rhs, {x: key}),
    )


@register(S + "EQX.RATIONAL")
def eqx_rational(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "EQX.RATIONAL"
    p_, q_ = rng.sample([v for v in range(-8, 9) if v], 2)
    if d == "easy":
        num = sympy.expand((x + p_) * (x + q_))
        expr = num / (x + p_)
        key = x + q_
        stem = (
            f"For $x \\ne {-p_}$, which expression is equivalent to $\\dfrac{{{tex(num)}}}{{{lin(1, p_)}}}$?"
        )
        dist = ds(
            (lambda: x - q_, "sign_flip", "Sign error when factoring."),
            (lambda: x + p_, "misread", "That's the factor that cancels, not what remains."),
            (lambda: x**2 + q_, "concept", "Canceled terms instead of factors."),
            (lambda: x + p_ * q_, "concept", "Divided only the constant term."),
        )
        steps = [
            f"Factor: ${tex(num)} = ({lin(1, p_)})({lin(1, q_)})$.",
            f"Cancel ${lin(1, p_)}$: ${tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(expr, key, {x: 11}) and holds(expr, key, {x: 13}),
        )
    if d == "medium":
        expr = 1 / (x + p_) + 1 / (x + q_)
        key = sympy.together(expr)
        stem = f"Which expression is equivalent to $\\dfrac{{1}}{{{lin(1, p_)}}} + \\dfrac{{1}}{{{lin(1, q_)}}}$?"
        dist = ds(
            (lambda: 2 / (2 * x + p_ + q_), "wrong_formula", "Added numerators and added denominators."),
            (
                lambda: 1 / ((x + p_) * (x + q_)),
                "partial_solution",
                "Found the common denominator but not the new numerator.",
            ),
            (
                lambda: (2 * x + p_ + q_) / (x**2 + p_ * q_),
                "distribution",
                "Expanded the denominator without the middle term.",
            ),
            (lambda: 2 / ((x + p_) * (x + q_)), "concept", "Added numerators without rescaling them."),
        )
        steps = [
            f"Common denominator $({lin(1, p_)})({lin(1, q_)})$.",
            f"Numerator: $({lin(1, q_)}) + ({lin(1, p_)}) = {lin(2, p_ + q_)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(expr, key, {x: 17}) and holds(expr, key, {x: R(1, 3)}),
        )
    a, b = ri(rng, 2, 7), ri(rng, -9, 9)
    c = ri(rng, -6, 6)
    while b == a * c:
        b = ri(rng, -9, 9)
    quo, rem = sympy.div(a * x + b, x + c, x)
    key = rem
    stem = (
        f"$$\\frac{{{lin(a, b)}}}{{{lin(1, c)}}} = A + \\frac{{B}}{{{lin(1, c)}}}$$ The equation above is true for all "
        f"$x \\ne {-c}$, where $A$ and $B$ are constants. What is the value of $B$?"
    )
    dist = ds(
        (lambda: b + a * c, "sign_flip", "Sign error: $B = b - ac$."),
        (lambda: quo, "misread", "That's $A$."),
        (lambda: R(b - c), "concept", f"Subtracted ${c}$ without multiplying by ${a}$."),
        (lambda: R(b), "partial_solution", "That's the original numerator constant."),
    )
    steps = [f"${lin(a, b)} = {a}({lin(1, c)}) + ({tex(rem)})$.", f"So $A = {a}$ and $B = {tex(rem)}$."]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds((a * x + b) / (x + c), quo + key / (x + c), {x: 23}),
    )


_A, _b, _h, _P, _l, _w, _d, _r, _t = sympy.symbols("A b h P ell w d r t", positive=True)
_F, _C, _V, _y, _m, _x0 = sympy.symbols("F C V y m x", positive=True)
_R, _a, _E, _v, _S, _n = sympy.symbols("R a E v S n", positive=True)
REARR = {
    "easy": [
        ("the area $A$ of a triangle with base $b$ and height $h$", _A, _b * _h / 2, _h,
         [(_A / (2 * _b), "operation_swap"), (2 * _A * _b, "operation_swap"), (_A * _b / 2, "operation_swap")]),
        ("the perimeter $P$ of a rectangle with length $\\ell$ and width $w$", _P, 2 * _l + 2 * _w, _w,
         [(_P / 2 - 2 * _l, "order_of_ops"), ((_P - _l) / 2, "distribution"), (_P - 2 * _l, "partial_solution")]),
        ("the distance $d$ traveled at rate $r$ for time $t$", _d, _r * _t, _t,
         [(_d * _r, "operation_swap"), (_r / _d, "reciprocal"), (_d - _r, "operation_swap")]),
    ],
    "medium": [
        ("the Fahrenheit temperature $F$ for a Celsius temperature $C$", _F, R(9, 5) * _C + 32, _C,
         [(R(5, 9) * _F - 32, "order_of_ops"), (R(9, 5) * (_F - 32), "reciprocal"), (R(5, 9) * (_F + 32), "sign_flip")]),
        ("the volume $V$ of a cone with radius $r$ and height $h$", _V, sympy.pi * _r**2 * _h / 3, _h,
         [(_V / (3 * sympy.pi * _r**2), "operation_swap"), (3 * _V * sympy.pi * _r**2, "operation_swap"), (3 * _V / (sympy.pi * _r), "exponent_rule")]),
        ("the value $y$ of a linear model with slope $m$ and intercept $b$ at input $x$", _y, _m * _x0 + _b, _x0,
         [(_y / _m - _b, "order_of_ops"), ((_y + _b) / _m, "sign_flip"), (_m * (_y - _b), "operation_swap")]),
    ],
    "hard": [
        ("the total resistance $R$ of two resistors $a$ and $b$ wired in parallel, $\\frac{1}{R} = \\frac{1}{a} + \\frac{1}{b}$", 1 / _R, 1 / _a + 1 / _b, _b,
         [(_R - _a, "wrong_formula"), (_a * _R / (_R - _a), "sign_flip"), ((_a - _R) / (_a * _R), "reciprocal")]),
        ("the amount $A$ after simple interest at rate $r$ for $t$ years on principal $P$", _A, _P * (1 + _r * _t), _r,
         [((_A - _P) / _t, "partial_solution"), (_A / (_P * _t) - 1, "order_of_ops"), ((_A - 1) / (_P * _t), "distribution")]),
        ("the kinetic energy $E$ of an object with mass $m$ and speed $v$", _E, _m * _v**2 / 2, _v,
         [(2 * _E / _m, "partial_solution"), (sympy.sqrt(_E / (2 * _m)), "operation_swap"), (sympy.sqrt(2 * _E * _m), "operation_swap")]),
        ("the sum $S$ of an arithmetic sequence with $n$ terms, first term $a$, and last term $\\ell$", _S, _n * (_a + _l) / 2, _l,
         [(2 * _S / _n + _a, "sign_flip"), (_S / (2 * _n) - _a, "operation_swap"), (2 * _S - _a * _n, "distribution")]),
    ],
}  # fmt: skip


@register(S + "EQX.REARR")
def eqx_rearr(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "EQX.REARR"
    desc, lhs, rhs, target, wrong = rng.choice(REARR[d])
    key = sympy.solve(sympy.Eq(lhs, rhs), target)[0]
    tname = tex(target)
    dist = [
        D(v, mo, f"Check by substituting back: this doesn't reproduce the formula. ({mo.replace('_', ' ')})")
        for v, mo in wrong
    ]
    stem = (
        f"The formula ${tex(lhs)} = {tex(rhs)}$ gives {desc}. Which equation correctly expresses ${tname}$ in "
        "terms of the other quantities?"
    )
    steps = [f"Undo each operation on ${tname}$ in reverse order.", f"${tname} = {tex(key)}$."]
    others = sorted(rhs.free_symbols | lhs.free_symbols - {target}, key=str)
    subs = {s_: v for s_, v in zip(others, [R(3), R(5), R(7), R(11)], strict=False)}

    def verify() -> bool:
        vals = dict(subs)
        vals[target] = key.subs(subs)
        return holds(lhs.subs(vals), rhs.subs(vals), {})

    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=verify,
        fmt=_eq_fmt(tname),
    )


# ---------- NLEQ: nonlinear equations ----------


@register(S + "NLEQ.QUAD")
def nleq_quad(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLEQ.QUAD"
    if d == "easy":
        r1, r2 = ri(rng, 1, 9), -ri(rng, 1, 9)
        while r1 == -r2:
            r2 = -ri(rng, 1, 9)
        poly = sympy.expand((x - r1) * (x - r2))
        key = max(sympy.solve(poly, x))
        stem = f"$${tex(poly)} = 0$$ What is the positive solution to the equation above?"
        dist = ds(
            (lambda: R(r2), "misread", "That's the negative solution."),
            (lambda: R(-r1), "sign_flip", f"Sign error: the factor $(x - {r1})$ gives $x = {r1}$."),
            (lambda: R(-r2), "sign_flip", f"Sign error: the factor $(x + {-r2})$ gives $x = {r2}$."),
            (lambda: R(r1 * r2), "misread", "That's the product of the solutions."),
        )
        steps = [
            f"Factor: $(x - {r1})(x + {-r2}) = 0$.",
            f"Solutions: $x = {r1}$ or $x = {r2}$; positive: ${r1}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(poly, 0, {x: key}) and key > 0,
        )
    if d == "medium":
        p_, r_ = rng.choice([(2, 1), (3, 1), (2, 3), (3, 2), (4, 1), (5, 2), (2, 5)])
        q_, s_ = ri(rng, -7, 7), ri(rng, -7, 7)
        poly = sympy.expand((p_ * x - q_) * (r_ * x - s_))
        a, b, c = (poly.coeff(x, i) for i in (2, 1, 0))
        key = sum(sympy.solve(poly, x)) if len(sympy.solve(poly, x)) == 2 else 2 * sympy.solve(poly, x)[0]
        stem = f"$${tex(poly)} = 0$$ What is the sum of the solutions to the equation above?"
        dist = ds(
            (lambda: b / a, "sign_flip", "The sum of the roots is $-b/a$."),
            (lambda: c / a, "misread", "That's the product of the solutions."),
            (lambda: -b, "partial_solution", f"Forgot to divide by the leading coefficient ${a}$."),
            (
                lambda: R(q_ + s_),
                "concept",
                "Added the constants in the factors without dividing by their coefficients.",
            ),
        )
        steps = [
            f"Factor: $({lin(p_, -q_)})({lin(r_, -s_)}) = 0$, so $x = {tex(R(q_, p_))}$ or $x = {tex(R(s_, r_))}$.",
            f"Sum: ${tex(key)}$ (also $-b/a$).",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(key, -b / a, {}),
        )
    b = 2 * ri(rng, -6, 6, (0,))
    c = ri(rng, -15, 10)
    q = R(b * b, 4) - c
    while q <= 0 or sympy.sqrt(q).is_Rational:
        c = ri(rng, -15, 10)
        q = R(b * b, 4) - c
    poly = x**2 + b * x + c
    roots = sympy.solve(poly, x)
    key = (roots[0] - roots[1]) ** 2 / 4
    stem = (
        f"$${tex(poly)} = 0$$ The solutions to the equation above can be written as $x = {-b // 2} \\pm \\sqrt{{k}}$, "
        "where $k$ is a constant. What is the value of $k$?"
    )
    dist = ds(
        (
            lambda: R(b * b - 4 * c),
            "wrong_formula",
            "That's the discriminant; dividing by $2a$ halves the root, so $k$ is a quarter of it.",
        ),
        (lambda: R(b * b, 4) + c, "sign_flip", "Sign error when completing the square."),
        (lambda: R(-c), "partial_solution", "Moved the constant but didn't add $(b/2)^2$ to both sides."),
        (lambda: sympy.sqrt(q), "misread", "That's $\\sqrt{k}$, not $k$."),
    )
    steps = [
        f"Complete the square: $(x {'+' if b > 0 else '-'} {abs(b) // 2})^2 = {tex(q)}$.",
        f"$x = {-b // 2} \\pm \\sqrt{{{tex(q)}}}$, so $k = {tex(q)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(poly, 0, {x: -b // 2 + sympy.sqrt(key)}),
    )


@register(S + "NLEQ.DISC")
def nleq_disc(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLEQ.DISC"
    if d == "easy":
        a, b = ri(rng, 1, 4), ri(rng, -10, 10)
        case = rng.choice(["zero", "one", "two"])
        disc_c = sympy.Rational(b * b, 4 * a)
        c = {
            "one": disc_c,
            "zero": sympy.floor(disc_c) + ri(rng, 1, 6),
            "two": sympy.ceiling(disc_c) - ri(rng, 1, 6),
        }[case]
        if case == "one" and not c.is_integer:
            b = 2 * a * ri(rng, -4, 4)
            c = R(b * b, 4 * a)
        poly = a * x**2 + b * x + c
        disc = sympy.discriminant(poly, x)
        found = "two" if disc > 0 else "one" if disc == 0 else "zero"
        labels = {
            "zero": "No real solutions",
            "one": "Exactly one real solution",
            "two": "Exactly two real solutions",
            "inf": "Infinitely many real solutions",
        }
        why = {
            "zero": "The discriminant is not negative.",
            "one": "The discriminant is not zero.",
            "two": "The discriminant is not positive.",
            "inf": "A quadratic has at most two solutions.",
        }
        key = labels[found]
        stem = f"$${tex(poly)} = 0$$ How many distinct real solutions does the equation above have?"
        dist = [D(v, "concept", why[c_]) for c_, v in labels.items() if c_ != found]
        steps = [
            f"Discriminant: $b^2 - 4ac = {b}^2 - 4({a})({tex(c)}) = {tex(disc)}$.",
            {
                "two": "Positive: two solutions.",
                "one": "Zero: one solution.",
                "zero": "Negative: no real solutions.",
            }[found],
        ]
        return build(rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps,
                     verify=lambda: len([r for r in sympy.solve(poly, x) if r.is_real]) == {"zero": 0, "one": 1, "two": 2}[found])  # fmt: skip
    if d == "medium":
        p_, q_ = ri(rng, 1, 5), ri(rng, 1, 7)
        a, c = p_ * p_, q_ * q_
        poly = a * x**2 + k * x + c
        key = max(sympy.solve(sympy.discriminant(poly, x), k))
        stem = f"$${a}x^2 + kx + {c} = 0$$ In the equation above, $k$ is a positive constant. If the equation has exactly one real solution, what is the value of $k$?"
        dist = ds(
            (lambda: R(4 * a * c), "partial_solution", "That's $k^2$; take the square root."),
            (lambda: R(p_ * q_), "wrong_formula", "Forgot the factor of 2: $k^2 = 4ac$."),
            (lambda: R(2 * (p_ + q_)), "concept", "Added the square roots instead of multiplying."),
            (lambda: R(a + c), "concept", "One solution requires $b^2 - 4ac = 0$, not $b = a + c$."),
        )
        steps = [
            "Exactly one solution: discriminant $k^2 - 4ac = 0$.",
            f"$k^2 = 4({a})({c}) = {4 * a * c}$, so $k = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: len(sympy.solve(poly.subs(k, key), x)) == 1,
        )
    a = ri(rng, 1, 4)
    b, c = ri(rng, -12, 12), ri(rng, -10, 10)
    f = a * x**2 + b * x + c
    minimum = f.subs(x, sympy.solve(sympy.diff(f, x), x)[0])
    sol = sympy.solve_univariate_inequality(sympy.discriminant(f - k, x) < 0, k, relational=False)
    key = sympy.ceiling(sol.sup) - 1
    stem = (
        f"$${tex(f)} = k$$ In the equation above, $k$ is a constant. What is the greatest integer value of $k$ "
        "for which the equation has no real solutions?"
    )
    dist = ds(
        (lambda: key + 1, "off_by_one", "With this $k$ the equation has a real solution."),
        (lambda: -minimum, "sign_flip", "Sign error computing the minimum."),
        (lambda: R(c), "misread", "That's the constant term (the $y$-intercept), not the minimum value."),
        (
            lambda: sympy.floor(minimum) - 1 if not minimum.is_integer else minimum - 2,
            "off_by_one",
            "Too small: a larger $k$ still has no solutions.",
        ),
    )
    steps = [
        f"$f(x) = {tex(f)}$ opens upward with minimum value ${tex(minimum)}$.",
        f"$f(x) = k$ has no real solutions exactly when $k < {tex(minimum)}$; the greatest such integer is ${tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: key < minimum <= key + 1,
    )


@register(S + "NLEQ.RADRAT")
def nleq_radrat(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLEQ.RADRAT"
    if d == "easy":
        a, b = ri(rng, -9, 9), ri(rng, 2, 9)
        lhs = sympy.sqrt(x + a)
        key = sympy.solve(sympy.Eq(lhs, b), x)[0]
        stem = f"$$\\sqrt{{{lin(1, a)}}} = {b}$$ What is the solution to the equation above?"
        dist = ds(
            (lambda: R(b - a), "partial_solution", "Forgot to square both sides."),
            (lambda: R(b * b + a), "sign_flip", "Sign error moving the constant."),
            (lambda: R(b * b), "partial_solution", "Squared but didn't subtract the constant."),
            (lambda: R(2 * b - a), "operation_swap", "Doubled instead of squaring."),
        )
        steps = [f"Square: ${lin(1, a)} = {b * b}$.", f"$x = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(lhs, b, {x: key}),
        )
    if d == "medium":
        b = ri(rng, -3, 5)
        r = b + ri(rng, 2, 7)
        a = (r - b) ** 2 - r
        ext = 2 * b + 1 - r
        lhs, rhs = sympy.sqrt(x + a), x - b
        sols = sympy.solve(sympy.Eq(lhs, rhs), x)
        key = sols[0]
        stem = f"$$\\sqrt{{{lin(1, a)}}} = {lin(1, -b)}$$ What is the solution to the equation above?"
        dist = ds(
            (
                lambda: R(ext),
                "extraneous",
                "Solves the squared equation, but makes the right side negative: extraneous.",
            ),
            (lambda: R(-r), "sign_flip", "Sign error when factoring."),
            (lambda: R(r - b), "misread", "That's the value of the square root, not of $x$."),
            (lambda: R(r + ext), "misread", "That's the sum of the roots of the squared equation."),
        )
        steps = [
            f"Square: ${lin(1, a)} = ({lin(1, -b)})^2$, so ${tex(sympy.expand((x - b) ** 2 - x - a))} = 0$.",
            f"Roots: ${r}$ and ${ext}$. Check: $x = {ext}$ makes ${lin(1, -b)}$ negative, so it's extraneous.",
            f"Solution: $x = {r}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: len(sols) == 1 and holds(lhs, rhs, {x: key}),
        )
    p_ = ri(rng, -7, 7)
    r = ri(rng, -9, 9, (0, p_))
    s_, t_ = p_ + r, -p_ * r
    lhs, rhs = x**2 / (x - p_), (s_ * x + t_) / (x - p_)
    sols = sympy.solve(sympy.Eq(lhs, rhs), x)
    key = sols[0]
    stem = (
        f"$$\\frac{{x^2}}{{{lin(1, -p_)}}} = \\frac{{{lin(s_, t_)}}}{{{lin(1, -p_)}}}$$ "
        "What is the solution to the equation above?"
    )
    dist = ds(
        (lambda: R(p_), "extraneous", f"$x = {p_}$ makes the denominator zero, so it is extraneous."),
        (lambda: R(-r), "sign_flip", "Sign error when factoring."),
        (lambda: R(s_), "misread", "That's the sum of the roots of the cleared equation."),
        (lambda: R(t_), "misread", "That's the product of the roots of the cleared equation."),
    )
    steps = [
        f"Multiply by ${lin(1, -p_)}$: $x^2 - ({lin(s_, t_)}) = 0$, i.e. $(x - {p_})(x - {r}) = 0$.".replace(
            "- -", "+ "
        ),
        f"$x = {p_}$ is excluded (zero denominator), so $x = {r}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: len(sols) == 1 and holds(lhs, rhs, {x: key}),
    )


xr = sympy.Symbol("x", real=True)


@register(S + "NLEQ.ABS")
def nleq_abs(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLEQ.ABS"
    if d == "easy":
        a, b = ri(rng, -9, 9), ri(rng, 1, 9)
        sols = sympy.solve(sympy.Eq(sympy.Abs(xr - a), b), xr)
        key = sum(sols)
        stem = f"$$|{lin(1, -a)}| = {b}$$ What is the sum of the solutions to the equation above?"
        dist = ds(
            (lambda: R(a + b), "partial_solution", "That's only one solution."),
            (lambda: R(2 * b), "misread", "Doubled the distance instead of the center."),
            (lambda: R(-2 * a), "sign_flip", "Sign error: $|x - a| = b$ is centered at $+a$."),
            (lambda: R(0), "concept", "The two solutions aren't opposites unless the center is 0."),
        )
        steps = [
            f"$x - {a} = {b}$ or $x - {a} = -{b}$: $x = {a + b}$ or $x = {a - b}$.".replace("- -", "+ "),
            f"Sum: ${tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: len(sols) == 2 and all(abs(s_ - a) == b for s_ in sols),
        )
    if d == "medium":
        a, b, c = ri(rng, 2, 5), ri(rng, -9, 9), ri(rng, 1, 12)
        sols = sympy.solve(sympy.Eq(sympy.Abs(a * xr + b), c), xr)
        key = abs(sols[0] - sols[1])
        stem = f"$$|{lin(a, b)}| = {c}$$ What is the positive difference between the two solutions to the equation above?"
        dist = ds(
            (lambda: R(c, a), "partial_solution", "That's half the difference."),
            (lambda: R(2 * c), "partial_solution", f"Forgot to divide by ${a}$."),
            (lambda: abs(R(2 * b, a)), "misread", "That's related to the center, not the spread."),
            (lambda: R(2 * c - b, a), "sign_flip", "Mixed the constant into the difference."),
        )
        steps = [
            f"${lin(a, b)} = \\pm {c}$ gives $x = {tex(sols[0])}$ or $x = {tex(sols[1])}$.",
            f"Difference: ${tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(abs(a * sols[0] + b), c, {}) and holds(abs(a * sols[1] + b), c, {}),
        )
    while True:
        a, c = ri(rng, -9, 9), ri(rng, -9, 9)
        sols = sympy.solve(sympy.Eq(sympy.Abs(xr - a), 2 * xr + c), xr)
        cands = [R(-a - c), R(a - c, 3)]
        ext = [v for v in cands if v not in sols]
        if len(sols) == 1 and ext:
            break
    key = sols[0]
    stem = f"$$|{lin(1, -a)}| = {lin(2, c)}$$ What is the solution to the equation above?"
    dist = ds(
        (
            lambda: ext[0],
            "extraneous",
            f"This comes from one case, but it makes ${lin(2, c)}$ negative: extraneous.",
        ),
        (lambda: -key, "sign_flip", "Sign error when splitting the cases."),
        (lambda: R(a + c), "sign_flip", "Sign errors when collecting terms."),
        (lambda: R(a - c), "partial_solution", "Forgot to divide by the coefficient of $x$."),
    )
    steps = [
        f"Case 1: $x - {a} = 2x + {c}$ gives $x = {tex(cands[0])}$. Case 2: $-(x - {a}) = 2x + {c}$ gives $x = {tex(cands[1])}$.".replace(
            "+ -", "- "
        ).replace("- -", "+ "),
        f"The right side must be $\\ge 0$; only $x = {tex(key)}$ works.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(abs(key - a), 2 * key + c, {}) and 2 * ext[0] + c < 0,
    )


@register(S + "NLEQ.SYS")
def nleq_sys(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLEQ.SYS"
    key: Value
    y_ = sympy.Symbol("y")
    if d == "easy":
        a = ri(rng, -6, 6)
        b = a + rng.choice([-ri(rng, 1, 5), 0, ri(rng, 1, 9)])
        sols = sympy.solve([sympy.Eq(y_, x**2 + a), sympy.Eq(y_, b)], [x, y_], dict=True)
        n = len([s_ for s_ in sols if s_[x].is_real])
        labels = ["Zero", "Exactly one", "Exactly two", "Exactly three"]
        key = labels[n]
        stem = f"$$y = {lin(1, a, 'x^2')}$$ $$y = {b}$$ How many solutions $(x, y)$ does the system of equations above have?"
        why = "A horizontal line meets this parabola 0, 1, or 2 times depending on whether it's below, at, or above the vertex."
        dist = [D(v, "concept", why) for v in labels if v != key]
        steps = [
            f"Substitute: $x^2 = {b - a}$.",
            f"{'Positive' if b > a else 'Zero' if b == a else 'Negative'}: {key.lower()} solution(s).",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: n == (2 if b > a else 1 if b == a else 0),
        )
    r1, r2 = rng.sample(range(-6, 8), 2)
    mv, dv = ri(rng, -4, 4), ri(rng, -9, 9)
    quad = sympy.expand((x - r1) * (x - r2)) + mv * x + dv
    if d == "medium":
        sols = sympy.solve([sympy.Eq(y_, quad), sympy.Eq(y_, mv * x + dv)], [x, y_], dict=True)
        key = sum(s_[x] for s_ in sols)
        stem = (
            f"$$y = {tex(quad)}$$ $$y = {lin(mv, dv)}$$ The system of equations above has two solutions "
            "$(x_1, y_1)$ and $(x_2, y_2)$. What is the value of $x_1 + x_2$?"
        )
        dist = ds(
            (lambda: -key, "sign_flip", "Sign error: the sum of roots of $x^2 + bx + c$ is $-b$."),
            (lambda: R(r1 * r2), "misread", "That's the product of the $x$-values."),
            (
                lambda: -quad.coeff(x, 1),
                "partial_solution",
                "Forgot to subtract the line's slope before using $-b/a$.",
            ),
            (lambda: sum(s_[y_] for s_ in sols), "misread", "That's $y_1 + y_2$."),
        )
        steps = [
            f"Set equal: ${tex(quad)} = {lin(mv, dv)}$, so ${tex(sympy.expand((x - r1) * (x - r2)))} = 0$.",
            f"$x = {r1}$ or $x = {r2}$; sum ${tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(key, r1 + r2, {}),
        )
    b, c = ri(rng, -8, 8), ri(rng, -9, 9)
    mv = ri(rng, -5, 5)
    f = x**2 + b * x + c
    key = sympy.solve(sympy.discriminant(f - (mv * x + k), x), k)[0]
    stem = (
        f"$$y = {tex(f)}$$ $$y = {lin(mv, 0)} + k$$ In the system above, $k$ is a constant. For what value of $k$ "
        "does the system have exactly one solution?"
    ).replace("$$y = 0 + k$$", "$$y = k$$")
    dist = ds(
        (
            lambda: R(c),
            "misread",
            "That's where the parabola crosses the $y$-axis, not where the line is tangent.",
        ),
        (lambda: -key, "sign_flip", "Sign error in the discriminant."),
        (lambda: c - R((b - mv) ** 2, 2), "wrong_formula", "Used $2$ instead of $4$ in $b^2 - 4ac$."),
        (lambda: c - R(b * b, 4), "partial_solution", "Ignored the line's slope when combining $x$-terms."),
        (lambda: c - (b - mv) ** 2, "wrong_formula", "Forgot the 4 in $b^2 - 4ac$."),
        (lambda: c + R((b - mv) ** 2, 4), "sign_flip", "Sign error isolating $k$."),
    )
    steps = [
        f"Set equal: $x^2 + ({b - mv})x + ({c} - k) = 0$.",
        f"One solution: $({b - mv})^2 - 4({c} - k) = 0$, so $k = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: len(sympy.solve(f - mv * x - key, x)) == 1,
    )


# ---------- NLF: nonlinear functions ----------


@register(S + "NLF.VERTEX")
def nlf_vertex(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLF.VERTEX"
    a = ri(rng, 1, 5) * rng.choice([1, -1])
    h, kv = ri(rng, -8, 8), ri(rng, -12, 12)
    if d == "easy":
        f = a * (x - h) ** 2 + kv
        crit = sympy.solve(sympy.diff(f, x), x)[0]
        word = "minimum" if a > 0 else "maximum"
        key = f.subs(x, crit)
        stem = f"The function $f$ is defined by $f(x) = {tex(a) if a not in (1, -1) else '-' if a == -1 else ''}(x {'-' if h >= 0 else '+'} {abs(h)})^2 {'+' if kv >= 0 else '-'} {abs(kv)}$. What is the {word} value of $f(x)$?"
        dist = ds(
            (lambda: R(h), "misread", "That's the $x$-coordinate of the vertex."),
            (lambda: -key, "sign_flip", "Sign error reading the vertex form."),
            (lambda: f.subs(x, 0), "concept", "That's $f(0)$, the $y$-intercept."),
            (lambda: R(a), "misread", "That's the leading coefficient."),
        )
        steps = [
            f"Vertex form $a(x - h)^2 + k$ has vertex $(h, k) = ({h}, {kv})$.",
            f"The {word} value is ${kv}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key == kv and all((f.subs(x, t) - key) * a >= 0 for t in range(-10, 11)),
        )
    if d == "medium":
        b, c = ri(rng, -12, 12, (0,)), ri(rng, -9, 9)
        f = a * x**2 + b * x + c
        key = sympy.solve(sympy.diff(f, x), x)[0]
        stem = f"The function $f$ is defined by $f(x) = {tex(f)}$. What is the $x$-coordinate of the vertex of the graph of $y = f(x)$ in the $xy$-plane?"
        dist = ds(
            (lambda: R(b, 2 * a), "sign_flip", "The vertex is at $x = -b/(2a)$; the sign was dropped."),
            (lambda: R(-b, a), "wrong_formula", "Forgot the 2 in $-b/(2a)$."),
            (lambda: f.subs(x, key), "misread", "That's the $y$-coordinate of the vertex."),
            (lambda: R(c), "misread", "That's the $y$-intercept."),
        )
        steps = [f"$x = -\\frac{{b}}{{2a}} = -\\frac{{{b}}}{{2({a})}} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(f.subs(x, key + 3), f.subs(x, key - 3), {}),
        )
    p_, q_ = rng.sample(range(-9, 10), 2)
    f = a * (x - p_) * (x - q_)
    crit = sympy.solve(sympy.diff(f, x), x)[0]
    key = f.subs(x, crit)
    word = "minimum" if a > 0 else "maximum"
    stem = f"The function $f$ is defined by $f(x) = {tex(a) if a not in (1, -1) else '-' if a == -1 else ''}(x {'-' if p_ >= 0 else '+'} {abs(p_)})(x {'-' if q_ >= 0 else '+'} {abs(q_)})$. What is the {word} value of $f$?"
    dist = ds(
        (lambda: crit, "misread", "That's the $x$-coordinate of the vertex, not the value of $f$ there."),
        (lambda: f.subs(x, 0), "concept", "That's $f(0)$, the $y$-intercept."),
        (
            lambda: f.subs(x, R(p_ - q_, 2)),
            "sign_flip",
            "The vertex is midway between the zeros: use $(p + q)/2$.",
        ),
        (lambda: -key, "sign_flip", "Sign error evaluating $f$ at the vertex."),
    )
    steps = [
        f"The zeros are ${p_}$ and ${q_}$, so the vertex is at $x = {tex(crit)}$.",
        f"$f({tex(crit)}) = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: all((f.subs(x, t) - key) * a >= 0 for t in range(-12, 13)),
    )


@register(S + "NLF.EXPF")
def nlf_expf(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLF.EXPF"
    t = sympy.Symbol("t")
    if d == "easy":
        p0, pct = ri(rng, 2, 20) * 100, ri(rng, 2, 15)
        grow = rng.choice([True, False])
        factor = 1 + R(pct, 100) * (1 if grow else -1)
        key = f"The value {'increases' if grow else 'decreases'} by {pct}% each year."
        stem = (
            f"The function $V(t) = {p0}({float(factor):g})^t$ models the value, in dollars, of an investment $t$ "
            f"years after it was made. What does ${float(factor):g}$ represent?"
        )
        dist = [
            D(
                f"The value {'increases' if grow else 'decreases'} by {float(factor) * 100:g}% each year.",
                "concept",
                "The factor includes the original 100%; the change is the part above (or below) 1.",
            ),
            D(
                f"The value {'increases' if grow else 'decreases'} by \\${pct} each year.",
                "concept",
                "Exponential change is a percent of the current value, not a fixed amount.",
            ),
            D(
                f"The value {'decreases' if grow else 'increases'} by {pct}% each year.",
                "sign_flip",
                f"A factor {'greater' if grow else 'less'} than 1 means {'growth' if grow else 'decay'}.",
            ),
            D(f"The initial value is \\${float(factor):g}.", "misread", f"The initial value is \\${p0}."),
        ]
        steps = [
            f"The base ${float(factor):g} = 1 {'+' if grow else '-'} {pct / 100:g}$, so each year the value is multiplied by it: a {pct}% {'increase' if grow else 'decrease'}."
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(factor, 1 + R(pct, 100) * (1 if grow else -1), {}),
        )
    if d == "medium":
        p0, per = ri(rng, 2, 50) * 10, ri(rng, 2, 8)
        mult = rng.choice([2, 3])
        word = {2: "doubles", 3: "triples"}[mult]
        key_expr = p0 * mult ** (t / per)
        key = f"$P(t) = {p0}({mult})^{{t/{per}}}$"
        stem = f"A population of {p0} bacteria {word} every {per} hours. Which function gives the population $t$ hours later?"
        dist = [
            D(
                f"$P(t) = {p0}({mult})^{{{per}t}}$",
                "operation_swap",
                f"This multiplies by {mult} {per} times every hour.",
            ),
            D(
                f"$P(t) = {p0}({mult * per})^t$",
                "wrong_formula",
                f"Combined the factor and the period; the growth is {mult}x per {per} hours.",
            ),
            D(
                f"$P(t) = {p0} + {mult}^{{t/{per}}}$",
                "concept",
                "The growth factor multiplies the starting population.",
            ),
            D(
                f"$P(t) = {p0}({mult})^t$",
                "partial_solution",
                f"This {word} every hour, not every {per} hours.",
            ),
        ]
        steps = [
            f"After $t$ hours there have been $t/{per}$ {word.replace('les', 'lings') if mult == 2 else 'triplings'}.",
            f"{key}.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key_expr.subs(t, 2 * per) == p0 * mult**2,
        )
    a = ri(rng, 2, 12) * rng.choice([1, 5])
    b = rng.choice([R(2), R(3), R(4), R(1, 2), R(3, 2)])
    u, v = a * b, a * b**3
    a_, b_ = sympy.symbols("a b", positive=True)
    sol = sympy.solve([sympy.Eq(a_ * b_, u), sympy.Eq(a_ * b_**3, v)], [a_, b_], dict=True)[0]
    key = sol[a_]
    stem = f"For the exponential function $f(x) = ab^x$, where $a$ and $b$ are positive constants, $f(1) = {tex(u)}$ and $f(3) = {tex(v)}$. What is the value of $f(0)$?"
    dist = ds(
        (lambda: sol[b_], "misread", "That's the growth factor $b$."),
        (lambda: u - (v - u) / 2, "wrong_formula", "Assumed linear change between the points."),
        (lambda: sol[b_] ** 2, "misread", "That's $b^2 = f(3)/f(1)$."),
        (lambda: u * sol[b_], "operation_swap", "Multiplied by $b$ instead of dividing (that's $f(2)$)."),
    )
    steps = [
        f"$\\frac{{f(3)}}{{f(1)}} = b^2 = {tex(v / u)}$, so $b = {tex(sol[b_])}$.",
        f"$f(0) = a = \\frac{{f(1)}}{{b}} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(key * b, u, {}) and holds(key * b**3, v, {}),
    )


@register(S + "NLF.POLYZ")
def nlf_polyz(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLF.POLYZ"
    if d == "easy":
        zs = rng.sample([v for v in range(-8, 9) if v], 3)
        f = (x - zs[0]) * (x - zs[1]) * (x - zs[2])
        zeros = set(sympy.solve(f, x))
        key = R(rng.choice(zs))
        cands = [(R(-z), "sign_flip", f"Sign error: the factor $(x - ({z}))$ gives $x = {z}$.") for z in zs]
        cands.append((f.subs(x, 0), "concept", "That's $f(0)$, the $y$-intercept."))
        dist = [D(v, mo, why) for v, mo, why in cands if v not in zeros]
        factors = "".join(f"({lin(1, -z)})" for z in zs)
        stem = f"The function $f$ is defined by $f(x) = {factors}$. Which of the following is a zero of $f$?"
        steps = [
            "A product is zero when a factor is zero.",
            f"Zeros: ${', '.join(str(z) for z in sorted(zs))}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: f.subs(x, key) == 0,
        )
    c3, c2, c1, c0 = 1, ri(rng, -6, 6), ri(rng, -9, 9), ri(rng, -9, 9)
    a = ri(rng, -4, 4, (0,))
    if d == "medium":
        p = c3 * x**3 + c2 * x**2 + c1 * x + c0
        key = sympy.rem(p, x - a, x)
        stem = f"What is the remainder when $p(x) = {tex(p)}$ is divided by ${lin(1, -a)}$?"
        dist = ds(
            (
                lambda: p.subs(x, -a),
                "sign_flip",
                f"Evaluated at $x = {-a}$; dividing by $(x - ({a}))$ means evaluating at ${a}$.",
            ),
            (lambda: R(c0), "misread", "That's $p(0)$, the constant term."),
            (
                lambda: sympy.quo(p, x - a, x).subs(x, 0),
                "misread",
                "That's the constant term of the quotient.",
            ),
            (lambda: p.subs(x, a) + a, "off_by_one", "Arithmetic slip evaluating $p$."),
        )
        steps = [f"Remainder theorem: remainder $= p({a})$.", f"$p({a}) = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(sympy.quo(p, x - a, x) * (x - a) + key, p, {x: 7}),
        )
    p = x**3 + k * x**2 + c1 * x + c0
    key = sympy.solve(p.subs(x, a), k)[0]
    stem = f"$$p(x) = x^3 + kx^2 {'+' if c1 >= 0 else '-'} {abs(c1)}x {'+' if c0 >= 0 else '-'} {abs(c0)}$$ In the polynomial above, $k$ is a constant. If ${lin(1, -a)}$ is a factor of $p(x)$, what is the value of $k$?"
    dist = ds(
        (
            lambda: sympy.solve(p.subs(x, -a), k)[0],
            "sign_flip",
            f"Used $p({-a}) = 0$; the factor $(x - ({a}))$ means $p({a}) = 0$.",
        ),
        (lambda: -key, "sign_flip", "Sign error solving for $k$."),
        (lambda: sympy.solve(p.subs(x, a) - 1, k)[0], "off_by_one", "Arithmetic slip evaluating $p$."),
        (
            lambda: sympy.solve(sympy.Eq(k * a + c0, 0), k)[0],
            "partial_solution",
            "Dropped terms when substituting.",
        ),
    )
    steps = [
        f"Factor theorem: $p({a}) = 0$.",
        f"${a**3} + {a * a}k + {c1 * a} + {c0} = 0$, so $k = {tex(key)}$.".replace("+ -", "- "),
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: sympy.rem(p.subs(k, key), x - a, x) == 0,
    )


@register(S + "NLF.NOTATION")
def nlf_notation(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLF.NOTATION"
    a, b = ri(rng, -5, 6, (0,)), ri(rng, -9, 9)
    t = ri(rng, -5, 5, (0, 1))
    if d == "easy":
        f = a * x**2 + b
        key = f.subs(x, t)
        stem = f"The function $f$ is defined by $f(x) = {tex(f)}$. What is the value of $f({t})$?"
        dist = ds(
            (lambda: (a * t) ** 2 + b, "exponent_rule", f"Squared ${a}$ too; only $x$ is squared."),
            (lambda: a * 2 * t + b, "operation_swap", "Doubled the input instead of squaring it."),
            (lambda: a * t**2 - b, "sign_flip", "Sign error on the constant."),
            (lambda: -a * t**2 + b, "sign_flip", "Treated $(-x)^2$ as negative."),
        )
        steps = [f"$f({t}) = {a}({t})^2 + ({b}) = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key == a * t * t + b,
        )
    if d == "medium":
        c = ri(rng, -6, 6)
        f, g = a * x + b, x**2 + c
        key = f.subs(x, g.subs(x, t))
        stem = f"The functions $f$ and $g$ are defined by $f(x) = {lin(a, b)}$ and $g(x) = {lin(1, c, 'x^2')}$. What is the value of $f(g({t}))$?"
        dist = ds(
            (lambda: g.subs(x, f.subs(x, t)), "misread", "That's $g(f(t))$: apply $g$ first."),
            (lambda: f.subs(x, t) * g.subs(x, t), "concept", "Composition isn't multiplication."),
            (lambda: f.subs(x, t) + g.subs(x, t), "concept", "Composition isn't addition."),
            (lambda: g.subs(x, t), "partial_solution", f"That's $g({t})$; you still need to apply $f$."),
        )
        steps = [f"$g({t}) = {tex(g.subs(x, t))}$.", f"$f({tex(g.subs(x, t))}) = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(a * (t * t + c) + b, key, {}),
        )
    p_, q_ = ri(rng, -4, 4, (0,)), ri(rng, -6, 6)
    expr = a * x**2 + b * x
    u = sympy.Symbol("u")
    f_of_u = expr.subs(x, u + p_)
    key = f_of_u.subs(u, q_)
    stem = f"For the function $f$, $f({lin(1, -p_)}) = {tex(expr)}$ for all values of $x$. What is the value of $f({q_})$?"
    dist = ds(
        (
            lambda: expr.subs(x, q_),
            "concept",
            f"Substituted ${q_}$ for $x$; you need $x - {p_} = {q_}$.".replace("- -", "+ "),
        ),
        (lambda: expr.subs(x, q_ - p_), "sign_flip", "Sign error solving $x - p = q$."),
        (
            lambda: expr.subs(x, q_) - p_,
            "concept",
            "Shifting the input isn't the same as shifting the output.",
        ),
        (lambda: -key, "sign_flip", "Sign error in the arithmetic."),
    )
    steps = [
        f"Set $x - {p_} = {q_}$, so $x = {q_ + p_}$.".replace("- -", "+ "),
        f"$f({q_}) = {tex(expr.subs(x, q_ + p_))} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(expr.subs(x, q_ + p_), key, {}),
    )


@register(S + "NLF.TRANSF")
def nlf_transf(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLF.TRANSF"
    h, kv = ri(rng, 1, 9), ri(rng, 1, 9)
    if d == "easy":
        right, up = rng.choice([True, False]), rng.choice([True, False])
        hh, kk = (h if right else -h), (kv if up else -kv)
        shifted = (x - hh) ** 2 + kk  # with f(x) = x^2, the vertex must move to (hh, kk)
        key = f"$y = f({lin(1, -hh)}) {'+' if kk > 0 else '-'} {abs(kk)}$"
        stem = f"The graph of $y = f(x)$ is shifted {h} units {'right' if right else 'left'} and {kv} units {'up' if up else 'down'}. Which equation describes the new graph?"
        dist = [
            D(
                f"$y = f({lin(1, hh)}) {'+' if kk > 0 else '-'} {abs(kk)}$",
                "sign_flip",
                f"Horizontal shifts go the opposite way from the sign: right {h} is $x - {h}$.",
            ),
            D(
                f"$y = f({lin(1, -kk)}) {'+' if hh > 0 else '-'} {abs(hh)}$",
                "misread",
                "Swapped the horizontal and vertical shifts.",
            ),
            D(
                f"$y = f({lin(1, hh)}) {'-' if kk > 0 else '+'} {abs(kk)}$",
                "sign_flip",
                "Both shift directions are reversed.",
            ),
            D(
                f"$y = f({lin(1, -hh)}) {'-' if kk > 0 else '+'} {abs(kk)}$",
                "sign_flip",
                "Vertical shift direction is reversed.",
            ),
        ]
        steps = ["Right $h$: replace $x$ with $x - h$. Up $k$: add $k$.", f"{key}."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: sympy.solve(sympy.diff(shifted, x), x) == [hh] and shifted.subs(x, hh) == kk,
        )
    if d == "medium":
        p_, q_ = ri(rng, -6, 6), ri(rng, -6, 6)
        g_shift = (h, kv)
        key = pt(p_ + h, q_ + kv)
        stem = f"The point $({p_}, {q_})$ lies on the graph of $y = f(x)$. If $g(x) = f(x - {h}) + {kv}$, which point must lie on the graph of $y = g(x)$?"
        dist = [
            D(pt(p_ - h, q_ + kv), "sign_flip", f"$f(x - {h})$ moves the graph right, not left."),
            D(pt(p_ + kv, q_ + h), "misread", "Swapped the horizontal and vertical shifts."),
            D(pt(p_ + h, q_ - kv), "sign_flip", f"$+{kv}$ outside moves the graph up."),
            D(pt(p_ - h, q_ - kv), "sign_flip", "Both shifts are reversed."),
        ]
        steps = [f"$g({p_ + h}) = f({p_}) + {kv} = {q_ + kv}$.", f"So {key} is on $g$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: g_shift == (h, kv),
        )
    a_, mx = ri(rng, -5, 5), ri(rng, -9, 9)
    c, b, dd = ri(rng, 2, 4), ri(rng, -5, 5, (0,)), ri(rng, -9, 9)
    f = -((x - a_) ** 2) + mx
    g = -c * f.subs(x, x + b) + dd
    crit = sympy.solve(sympy.diff(g, x), x)[0]
    key = g.subs(x, crit)
    stem = (
        f"The function $f$ has a maximum value of ${mx}$ at $x = {a_}$. The function $g$ is defined by "
        f"$g(x) = -{c}f({lin(1, b)}) {'+' if dd >= 0 else '-'} {abs(dd)}$. What is the minimum value of $g$?"
    )
    dist = ds(
        (
            lambda: R(c * mx + dd),
            "sign_flip",
            "The $-$ sign flips the maximum into a minimum: multiply by $-" + str(c) + "$.",
        ),
        (lambda: R(-mx + dd), "partial_solution", f"Forgot to stretch by ${c}$."),
        (lambda: crit, "misread", "That's where the minimum occurs, not its value."),
        (lambda: R(-c * mx - dd), "sign_flip", "Sign error on the vertical shift."),
    )
    steps = [
        f"Multiplying by $-{c}$ turns the max ${mx}$ into a min ${-c * mx}$; the horizontal shift doesn't change values.",
        f"Add ${dd}$: minimum value ${tex(key)}$ (at $x = {tex(crit)}$).",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(key, -c * mx + dd, {}) and all(g.subs(x, t) >= key for t in range(-15, 15)),
    )


@register(S + "NLF.RATRAD")
def nlf_ratrad(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "NLF.RATRAD"
    if d == "easy":
        a, b, c = ri(rng, -9, 9), ri(rng, -6, 6), ri(rng, 1, 9)
        f = c / (x - a) + b
        key = sympy.solve(sympy.denom(sympy.together(f)), x)[0]
        stem = f"The function $f$ is defined by $f(x) = \\dfrac{{{c}}}{{{lin(1, -a)}}} {'+' if b >= 0 else '-'} {abs(b)}$. For what value of $x$ is $f(x)$ undefined?"
        dist = ds(
            (lambda: R(-a), "sign_flip", "The denominator is zero at $x = a$ for $x - a$."),
            (lambda: R(b), "misread", "That's the horizontal asymptote $y$-value."),
            (lambda: R(c), "misread", "That's the numerator."),
            (lambda: R(0), "concept", "$f(0)$ is defined here; only a zero denominator is a problem."),
        )
        steps = [f"Undefined when ${lin(1, -a)} = 0$: $x = {a}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: sympy.together(f).as_numer_denom()[1].subs(x, key) == 0,
        )
    if d == "medium":
        a, b = ri(rng, 2, 6), ri(rng, -12, 15, (0,))
        f = sympy.sqrt(a * x - b)
        key = sympy.solve(a * x - b, x)[0]
        stem = f"The function $f$ is defined by $f(x) = \\sqrt{{{lin(a, -b)}}}$. What is the least value of $x$ for which $f(x)$ is a real number?"
        dist = ds(
            (lambda: -key, "sign_flip", "Sign error solving $ax - b \\ge 0$."),
            (lambda: R(b), "partial_solution", f"Forgot to divide by ${a}$."),
            (lambda: R(a, b), "reciprocal", "Inverted the fraction."),
            (lambda: R(0), "concept", "The radicand, not $x$, must be nonnegative."),
        )
        steps = [f"Need ${lin(a, -b)} \\ge 0$, so $x \\ge {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: f.subs(x, key) == 0 and not f.subs(x, key - R(1, 10)).is_real,
        )
    p_, r_ = ri(rng, -9, 9, (0,)), ri(rng, 1, 6)
    q_, s_, t_ = ri(rng, -9, 9), ri(rng, -9, 9), ri(rng, 1, 9)
    f = (p_ * x**2 + q_) / (r_ * x**2 + s_ * x + t_)
    key = sympy.limit(f, x, sympy.oo)
    stem = f"The function $f$ is defined by $f(x) = \\dfrac{{{tex(p_ * x**2 + q_)}}}{{{tex(r_ * x**2 + s_ * x + t_)}}}$. The graph of $y = f(x)$ has a horizontal asymptote at $y = c$. What is the value of $c$?"
    dist = ds(
        (lambda: R(q_, t_), "misread", "That's $f(0)$, the ratio of the constant terms."),
        (lambda: R(r_, p_), "reciprocal", "Inverted the ratio of leading coefficients."),
        (lambda: R(p_), "partial_solution", "Forgot to divide by the denominator's leading coefficient."),
        (
            lambda: R(0),
            "concept",
            "Degrees are equal, so the asymptote is the ratio of leading coefficients, not 0.",
        ),
    )
    steps = ["Numerator and denominator have the same degree.", f"$c = \\frac{{{p_}}}{{{r_}}} = {tex(key)}$."]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: abs(sympy.N(f.subs(x, 10**8)) - key) < 1e-6,
    )
