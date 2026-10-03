"""Geometry and Trigonometry generators (MATH.GEO.*)."""

import math
import random
from typing import Any

import sympy

from app.generators.core import Difficulty, Generated, R, build, ds, holds, register, ri, tex, x

S = "MATH.GEO."
pi = sympy.pi
TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41)]


def _triangle_fig(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float],
                  labels: list[tuple[tuple[float, float], str]], right_at: str | None = None,
                  names: tuple[str, str, str] = ("A", "B", "C")) -> dict[str, Any]:  # fmt: skip
    return {
        "kind": "shape",
        "points": {names[0]: list(a), names[1]: list(b), names[2]: list(c)},
        "segments": [[names[0], names[1]], [names[1], names[2]], [names[2], names[0]]],
        "labels": [{"at": list(p), "text": t} for p, t in labels],
        "right_angles": [right_at] if right_at else [],
    }


def _mid(
    p: tuple[float, float], q: tuple[float, float], off: tuple[float, float] = (0, 0)
) -> tuple[float, float]:
    return ((p[0] + q[0]) / 2 + off[0], (p[1] + q[1]) / 2 + off[1])


# ---------- AV: area and volume ----------


@register(S + "AV.AREA")
def av_area(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "AV.AREA"
    if d == "easy":
        length, width = ri(rng, 5, 20), ri(rng, 2, 15)
        per = 2 * (length + width)
        w_ = sympy.solve(sympy.Eq(2 * length + 2 * x, per), x)[0]
        key = length * w_
        stem = f"A rectangle has a perimeter of {per} centimeters and a length of {length} centimeters. What is the area of the rectangle, in square centimeters?"
        dist = ds(
            (lambda: w_, "partial_solution", "That's the width."),
            (lambda: R(per * length), "wrong_formula", "Multiplied the perimeter by the length."),
            (
                lambda: length * (per - length),
                "wrong_formula",
                "Width is half the perimeter minus the length, not the perimeter minus the length.",
            ),
            (
                lambda: length * (R(per, 2) + length),
                "sign_flip",
                "Added the length instead of subtracting it.",
            ),
        )
        steps = [
            f"Width: $\\frac{{{per}}}{{2}} - {length} = {tex(w_)}$.",
            f"Area: ${length} \\times {tex(w_)} = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key == length * width,
        )
    if d == "medium":
        b, h, c = ri(rng, 4, 14), ri(rng, 3, 12), ri(rng, -3, 10)
        verts = [(0, 0), (b, 0), (c, h)]
        key = sympy.Polygon(*verts).area
        stem = f"In the $xy$-plane, a triangle has vertices at $(0, 0)$, $({b}, 0)$, and $({c}, {h})$. What is the area of the triangle?"
        fig: dict[str, Any] = {"kind": "plot", "x": [min(0, c) - 1, max(b, c) + 1], "y": [-1, h + 1], "polygons": [[list(v) for v in verts]],
               "points": [[vx, vy, f"({vx}, {vy})"] for vx, vy in verts]}  # fmt: skip
        dist = ds(
            (lambda: R(b * h), "wrong_formula", "Forgot the $\\frac{1}{2}$."),
            (
                lambda: R(b * c, 2) if c else R(b + h),
                "misread",
                "Used the $x$-coordinate of the top vertex as the height.",
            ),
            (lambda: R(b + h, 2), "wrong_formula", "Added base and height."),
            (lambda: R(b * h, 4), "operation_swap", "Halved twice."),
        )
        steps = [
            f"Base along the $x$-axis: ${b}$; height: ${h}$ (the $y$-coordinate of the top vertex).",
            f"Area $= \\frac{{1}}{{2}}({b})({h}) = {tex(key)}$.",
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
            verify=lambda: holds(key, R(abs(b * h), 2), {}),
        )
    s_ = 2 * ri(rng, 2, 9)
    key = s_**2 - pi * (s_ // 2) ** 2
    stem = f"A circle is inscribed in a square with side length {s_}. What is the area of the region inside the square but outside the circle?"
    fig = {"kind": "shape", "points": {"P": [0, 0], "Q": [s_, 0], "R": [s_, s_], "T": [0, s_]},
           "segments": [["P", "Q"], ["Q", "R"], ["R", "T"], ["T", "P"]], "circles": [{"c": [s_ / 2, s_ / 2], "r": s_ / 2}],
           "labels": [{"at": [s_ / 2, -0.6], "text": str(s_)}]}  # fmt: skip
    dist = ds(
        (
            lambda: s_**2 - pi * s_**2,
            "wrong_formula",
            "Used the side length as the radius; the radius is half the side.",
        ),
        (lambda: pi * (s_ // 2) ** 2, "misread", "That's the area of the circle."),
        (
            lambda: s_**2 - 2 * pi * (s_ // 2),
            "wrong_formula",
            "Subtracted the circumference instead of the area.",
        ),
        (lambda: 4 * s_ - 2 * pi * (s_ // 2), "concept", "That's a difference of perimeters, not areas."),
    )
    steps = [
        f"Square: ${s_ * s_}$. Circle radius ${s_ // 2}$: area ${tex(pi * (s_ // 2) ** 2)}$.",
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
        figure=fig,
        spr=False,
        verify=lambda: abs(float(key) - (s_ * s_ - math.pi * (s_ / 2) ** 2)) < 1e-9,
    )


@register(S + "AV.VOL")
def av_vol(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "AV.VOL"
    if d == "easy":
        l_, w_, h_ = ri(rng, 2, 12), ri(rng, 2, 12), ri(rng, 2, 12)
        key = R(l_ * w_ * h_)
        stem = f"A rectangular box is {l_} inches long, {w_} inches wide, and {h_} inches tall. What is its volume, in cubic inches?"
        dist = ds(
            (lambda: R(2 * (l_ * w_ + l_ * h_ + w_ * h_)), "wrong_formula", "That's the surface area."),
            (lambda: R(l_ * w_), "partial_solution", "That's the area of the base."),
            (lambda: R(l_ + w_ + h_), "wrong_formula", "Added the dimensions instead of multiplying."),
            (lambda: R(l_ * w_ * h_, 3), "wrong_formula", "Used the pyramid formula."),
        )
        steps = [f"$V = {l_} \\times {w_} \\times {h_} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key == l_ * w_ * h_,
        )
    if d == "medium":
        dia, h_ = 2 * ri(rng, 1, 8), ri(rng, 2, 15)
        key = pi * (dia // 2) ** 2 * h_
        stem = f"A cylinder has a diameter of {dia} meters and a height of {h_} meters. What is its volume, in cubic meters?"
        dist = ds(
            (lambda: pi * dia**2 * h_, "wrong_formula", "Used the diameter as the radius."),
            (lambda: 2 * pi * (dia // 2) * h_, "wrong_formula", "That's the lateral surface area."),
            (lambda: pi * (dia // 2) ** 2 * h_ / 3, "wrong_formula", "That's a cone's volume."),
            (lambda: pi * (dia // 2) * h_, "exponent_rule", "Forgot to square the radius."),
        )
        steps = [f"Radius ${dia // 2}$.", f"$V = \\pi r^2 h = \\pi({dia // 2})^2({h_}) = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            spr=False,
            verify=lambda: abs(float(key) - math.pi * (dia / 2) ** 2 * h_) < 1e-9,
        )
    r_ = 3 * ri(rng, 1, 6)
    h_ = sympy.Symbol("h", positive=True)
    key = sympy.solve(sympy.Eq(pi * r_**2 * h_, R(4, 3) * pi * r_**3), h_)[0]
    stem = f"A sphere has a radius of {r_} centimeters. A cylinder with the same radius has the same volume as the sphere. What is the height of the cylinder, in centimeters?"
    dist = ds(
        (lambda: R(4 * r_), "wrong_formula", "Dropped the $\\frac{1}{3}$ from the sphere formula."),
        (lambda: R(r_), "concept", "Equal radii don't mean equal heights."),
        (lambda: R(2 * r_), "concept", "That's the sphere's diameter."),
        (lambda: R(4, 3) * r_**2, "exponent_rule", "Cancelled only one factor of $r$."),
    )
    steps = [
        "$\\pi r^2 h = \\frac{4}{3}\\pi r^3$, so $h = \\frac{4}{3}r$.",
        f"$h = \\frac{{4}}{{3}}({r_}) = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(pi * r_**2 * key, R(4, 3) * pi * r_**3, {}),
    )


@register(S + "AV.SCALE")
def av_scale(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "AV.SCALE"
    if d == "easy":
        k_ = ri(rng, 2, 6)
        key = R(k_**2)
        stem = f"Each side of a square is multiplied by {k_}. By what factor is the area of the square multiplied?"
        dist = ds(
            (lambda: R(k_), "concept", "Area scales by the square of the length factor."),
            (lambda: R(2 * k_), "operation_swap", "Doubled the factor instead of squaring it."),
            (lambda: R(k_**3), "wrong_formula", "Cubing is for volume."),
            (lambda: R(4 * k_), "concept", "That's how the perimeter of four sides would add up."),
        )
        steps = [f"Area factor $= {k_}^2 = {k_ * k_}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key == R((k_ * 5) ** 2, 25),
        )
    if d == "medium":
        k_, v = ri(rng, 2, 4), ri(rng, 2, 30)
        key = R(v * k_**3)
        stem = f"A cube has a volume of {v} cubic centimeters. Each edge of the cube is multiplied by {k_}. What is the volume of the new cube, in cubic centimeters?"
        dist = ds(
            (lambda: R(v * k_), "concept", "Volume scales by the cube of the length factor."),
            (lambda: R(v * k_**2), "wrong_formula", "Squaring is for area."),
            (lambda: R(v * 3 * k_), "operation_swap", "Multiplied by $3k$ instead of $k^3$."),
            (lambda: R(v + k_**3), "operation_swap", "Added the factor instead of multiplying."),
        )
        steps = [f"Volume factor ${k_}^3 = {k_**3}$.", f"${v} \\times {k_**3} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key == (k_ * sympy.cbrt(v)) ** 3,
        )
    side_pct = rng.choice([10, 20, 30, 40, 50, 60])
    area_pct = (100 + side_pct) ** 2 // 100 - 100
    q = sympy.Symbol("q", positive=True)
    key = sympy.solve(sympy.Eq((1 + q / 100) ** 2, 1 + R(area_pct, 100)), q)[0]
    stem = f"The length and width of a rectangle are each increased by the same percent. As a result, the area increases by {area_pct}%. By what percent was each dimension increased?"
    dist = ds(
        (
            lambda: R(area_pct, 2),
            "concept",
            "Halving the area percent ignores that the two increases compound.",
        ),
        (lambda: R(area_pct), "concept", "Each dimension's change is smaller than the area's change."),
        (
            lambda: sympy.sqrt(area_pct),
            "wrong_formula",
            "Took the square root of the percent instead of the growth factor.",
        ),
        (lambda: R(area_pct, 4), "operation_swap", "Divided by 4."),
    )
    steps = [
        f"Area factor ${1 + area_pct / 100:g} = (1 + p)^2$.",
        f"$1 + p = {1 + side_pct / 100:g}$, so the increase is ${tex(key)}\\%$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        fmt=lambda v: v if isinstance(v, str) else f"${tex(v)}\\%$",
        verify=lambda: key == side_pct,
    )


# ---------- LAT: lines, angles, triangles ----------


def _parallel_fig(theta: float, marks: dict[str, tuple[str, str]]) -> dict[str, Any]:
    """Two horizontal parallel lines cut by a transversal at angle theta (degrees).
    marks: {label_text: (line 'P'|'Q', region 'ur'|'ul'|'ll'|'lr')}."""
    t = math.radians(theta)
    px, qx = 3.0, 3.0 + 4 / math.tan(t)
    pts: dict[str, list[float]] = {"L1a": [0, 0], "L1b": [12, 0], "L2a": [0, 4], "L2b": [12, 4],
           "T1": [px - 1.5 / math.tan(t), -1.5], "T2": [qx + 1.5 / math.tan(t), 5.5]}  # fmt: skip
    centers = {"P": (px, 0.0), "Q": (qx, 4.0)}
    ang = {"ur": theta / 2, "ul": 90 + theta / 2, "ll": 180 + theta / 2, "lr": 270 + theta / 2}
    labels = [
        {"at": [8, 0.35], "text": "ℓ"},
        {"at": [8, 4.35], "text": "m"},
        {"at": list(pts["T2"]), "text": "t"},
    ]
    for text, (where, region) in marks.items():
        cx, cy = centers[where]
        a = math.radians(ang[region])
        # Labels are centered text ~1.5 units wide, so push them clear of the transversal.
        dx = 0.9 * math.cos(a) + (1.0 if math.cos(a) > 0 else -1.0)
        labels.append({"at": [cx + dx, cy + 0.7 * math.sin(a)], "text": text})
    return {
        "kind": "shape",
        "points": pts,
        "segments": [["L1a", "L1b"], ["L2a", "L2b"], ["T1", "T2"]],
        "labels": labels,
        "hide_points": True,
    }


def _region_angle(theta: int, region: str) -> int:
    return theta if region in ("ur", "ll") else 180 - theta


@register(S + "LAT.ANGLES")
def lat_angles(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LAT.ANGLES"
    theta = rng.choice([35, 40, 48, 55, 62, 65, 70, 72, 75, 80])
    regions = ["ur", "ul", "ll", "lr"]
    r1, r2 = rng.choice(regions), rng.choice(regions)
    w1, w2 = "P", "Q"
    true1, true2 = _region_angle(theta, r1), _region_angle(theta, r2)
    same = true1 == true2
    intro = "In the figure, line $\\ell$ is parallel to line $m$, and both are intersected by line $t$."
    if d == "easy":
        fig = _parallel_fig(theta, {f"{true1}°": (w1, r1), "x°": (w2, r2)})
        key = sympy.solve(sympy.Eq(x, true1) if same else sympy.Eq(x + true1, 180), x)[0]
        stem = f"{intro} What is the value of $x$?"
        dist = ds(
            (
                lambda: R(180 - true1) if same else R(true1),
                "concept",
                "Decide whether the angles are congruent (same position) or supplementary.",
            ),
            (
                lambda: R(90 - true1) if true1 < 90 else R(true1 - 90),
                "concept",
                "These angles aren't complementary.",
            ),
            (lambda: R(360 - true1), "wrong_formula", "Angles on a straight line sum to 180°, not 360°."),
            (lambda: R(true1 + 90), "concept", "No right angle is involved."),
        )
        steps = ["Angles in matching positions at the two intersections are equal; angles in adjacent positions are supplementary.",
                 f"So $x = {tex(key)}$."]  # fmt: skip
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            verify=lambda: key == true2,
        )
    a, c = ri(rng, 2, 6), ri(rng, 2, 6)
    while a == c:
        c = ri(rng, 2, 6)
    xv = ri(rng, 6, 25)
    b = true1 - a * xv
    dv = true2 - c * xv
    e1, e2 = a * x + b, c * x + dv
    fig = _parallel_fig(theta, {f"({tex(e1)})°": (w1, r1), f"({tex(e2)})°": (w2, r2)})
    sol = sympy.solve(sympy.Eq(e1, e2) if same else sympy.Eq(e1 + e2, 180), x)[0]
    wrong = sympy.solve(sympy.Eq(e1 + e2, 180) if same else sympy.Eq(e1, e2), x)
    if d == "medium":
        key = sol
        stem = f"{intro} What is the value of $x$?"
        dist = ds(
            (
                lambda: wrong[0] if wrong else None,
                "concept",
                "Used the wrong relationship (equal vs. supplementary) for these positions.",
            ),
            (lambda: R(true1), "misread", "That's an angle measure, not $x$."),
            (
                lambda: sympy.solve(sympy.Eq(e1 + e2, 90), x)[0],
                "concept",
                "These angles aren't complementary.",
            ),
            (lambda: -sol, "sign_flip", "Sign error solving the equation."),
        )
        rel = "equal" if same else "supplementary"
        steps = [
            f"The marked angles are {rel}.",
            f"{'$' + tex(e1) + ' = ' + tex(e2) + '$' if same else '$' + tex(e1 + e2) + ' = 180$'}, so $x = {tex(key)}$.",
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
            verify=lambda: holds(e1, true1, {x: key}) and holds(e2, true2, {x: key}),
        )
    key = e2.subs(x, sol)
    stem = f"{intro} What is the measure, in degrees, of the angle labeled $({tex(e2)})°$?"
    dist = ds(
        (lambda: sol, "misread", "That's the value of $x$, not the angle."),
        (
            lambda: e2.subs(x, wrong[0]) if wrong else None,
            "concept",
            "Used the wrong relationship (equal vs. supplementary).",
        ),
        (lambda: 180 - key, "concept", "That's the measure of the adjacent angle."),
        (lambda: e1.subs(x, sol) if not same else 90 - key, "misread", "That's the other labeled angle."),
    )
    steps = [f"Solve for $x$: $x = {tex(sol)}$.", f"Angle: ${tex(e2.subs(x, sol))}°$."]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        figure=fig,
        verify=lambda: key == true2,
    )


@register(S + "LAT.TRI")
def lat_tri(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LAT.TRI"
    if d == "easy":
        a, b = ri(rng, 20, 90), ri(rng, 20, 70)
        key = sympy.solve(sympy.Eq(a + b + x, 180), x)[0]
        stem = f"In triangle $ABC$, the measure of angle $A$ is ${a}°$ and the measure of angle $B$ is ${b}°$. What is the measure, in degrees, of angle $C$?"
        dist = ds(
            (lambda: R(360 - a - b), "wrong_formula", "Triangle angles sum to 180°, not 360°."),
            (lambda: R(a + b), "concept", f"That's the exterior angle at $C$ ($180 - C$ = {a + b})."),
            (lambda: R(90 - a + b) if 90 - a + b > 0 else R(abs(a - b)), "concept", "Not a right triangle."),
            (lambda: key + 10, "off_by_one", "Arithmetic slip."),
        )
        steps = [f"$C = 180 - {a} - {b} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key + a + b == 180,
        )
    if d == "medium":
        apex = 2 * ri(rng, 10, 80)
        key = sympy.solve(sympy.Eq(apex + 2 * x, 180), x)[0]
        stem = f"In isosceles triangle $PQR$, $PQ = PR$ and the measure of angle $P$ is ${apex}°$. What is the measure, in degrees, of angle $Q$?"
        dist = ds(
            (
                lambda: R(180 - apex),
                "partial_solution",
                "That's the sum of the two base angles; split it in half.",
            ),
            (lambda: R(apex), "concept", "The equal angles are opposite the equal sides: $Q$ and $R$."),
            (lambda: R(180 - 2 * apex) if apex < 90 else None, "misread", "Treated $P$ as a base angle."),
            (lambda: R(apex, 2), "concept", "Halved the apex angle instead."),
        )
        steps = ["$Q = R$ and $P + Q + R = 180$.", f"$Q = \\frac{{180 - {apex}}}{{2}} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: apex + 2 * key == 180,
        )
    xv = ri(rng, 8, 20)
    a, c = ri(rng, 2, 5), ri(rng, 1, 4)
    b = ri(rng, -10, 20)
    dd = ri(rng, 0, 15)
    ang_a, ang_b = a * xv + b, c * xv + dd
    while ang_a <= 5 or ang_b <= 5 or ang_a + ang_b >= 175:
        xv = ri(rng, 8, 20)
        ang_a, ang_b = a * xv + b, c * xv + dd
    e_coef = rng.choice([a + c - 1, a + c + 1]) if a + c > 2 else a + c + 1
    e_const = ang_a + ang_b - e_coef * xv
    ext, e_a, e_b = e_coef * x + e_const, a * x + b, c * x + dd
    sol = sympy.solve(sympy.Eq(ext, e_a + e_b), x)[0]
    key = 180 - ext.subs(x, sol)
    stem = (
        f"In triangle $ABC$, the measure of angle $A$ is $({tex(e_a)})°$ and the measure of angle $B$ is $({tex(e_b)})°$. "
        f"The exterior angle at $C$ measures $({tex(ext)})°$. What is the measure, in degrees, of angle $C$ (inside the triangle)?"
    )
    dist = ds(
        (lambda: ext.subs(x, sol), "misread", "That's the exterior angle."),
        (lambda: sol, "misread", "That's the value of $x$."),
        (
            lambda: 180 - sympy.solve(sympy.Eq(ext + e_a + e_b, 180), x)[0],
            "concept",
            "The exterior angle equals the sum of the two remote interior angles; it doesn't add to them to make 180.",
        ),
        (lambda: e_a.subs(x, sol), "misread", "That's angle $A$."),
    )
    steps = [f"Exterior angle = sum of remote interior angles: ${tex(ext)} = {tex(e_a + e_b)}$, so $x = {tex(sol)}$.",
             f"Exterior angle $= {tex(ext.subs(x, sol))}°$; angle $C = 180 - {tex(ext.subs(x, sol))} = {tex(key)}°$."]  # fmt: skip
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(key + ang_a + ang_b, 180, {}) and sol == xv,
    )


@register(S + "LAT.SIMCONG")
def lat_simcong(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "LAT.SIMCONG"
    if d == "easy":
        ab, bc = ri(rng, 3, 12), ri(rng, 3, 12)
        scale = rng.choice([R(2), R(3), R(3, 2), R(5, 2), R(1, 2)])
        de = ab * scale
        key = sympy.solve(sympy.Eq(x / bc, de / ab), x)[0]
        stem = f"Triangle $ABC$ is similar to triangle $DEF$, where $A$ corresponds to $D$ and $B$ corresponds to $E$. If $AB = {ab}$, $BC = {bc}$, and $DE = {tex(de)}$, what is the length of $EF$?"
        dist = ds(
            (lambda: bc / scale, "reciprocal", "Divided by the scale factor instead of multiplying."),
            (lambda: bc + de - ab, "wrong_formula", "Similar figures scale by multiplying, not adding."),
            (lambda: de, "misread", "That's $DE$."),
            (lambda: R(bc), "concept", "Similar doesn't mean congruent."),
        )
        steps = [
            f"Scale factor $\\frac{{DE}}{{AB}} = {tex(scale)}$.",
            f"$EF = {bc} \\times {tex(scale)} = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(key / bc, de / ab, {}),
        )
    ad, db = ri(rng, 2, 9), ri(rng, 2, 9)
    de = ri(rng, 2, 12)
    ab = ad + db
    A, B, C = (0.0, 0.0), (10.0, 0.0), (3.0, 6.0)
    t_ = ad / ab
    D_, E_ = (
        (A[0] + t_ * (C[0] - A[0]), A[1] + t_ * (C[1] - A[1])),
        (A[0] + t_ * (B[0] - A[0]), A[1] + t_ * (B[1] - A[1])),
    )
    fig = {"kind": "shape", "points": {"A": list(A), "B": list(B), "C": list(C), "D": list(D_), "E": list(E_)},
           "segments": [["A", "B"], ["B", "C"], ["C", "A"], ["D", "E"]], "labels": []}  # fmt: skip
    # D on AC, E on AB, DE ∥ CB. Lengths given along AB.
    intro = f"In the figure, $D$ lies on $\\overline{{AC}}$, $E$ lies on $\\overline{{AB}}$, and $\\overline{{DE}}$ is parallel to $\\overline{{CB}}$. $AE = {ad}$ and $EB = {db}$."
    if d == "medium":
        key = sympy.solve(sympy.Eq(x / de, R(ab, ad)), x)[0]
        stem = f"{intro} If $DE = {de}$, what is the length of $CB$?"
        dist = ds(
            (lambda: R(de * db, ad), "misread", "Used $EB$ instead of the whole side $AB$."),
            (lambda: R(de * ad, ab), "reciprocal", "Set up the proportion upside down."),
            (lambda: R(de + db), "wrong_formula", "Similar figures scale by multiplying, not adding."),
            (lambda: R(de * ab, db), "misread", "Matched the wrong segments."),
        )
        steps = [
            f"Triangle $ADE \\sim$ triangle $ACB$ with ratio $\\frac{{AB}}{{AE}} = \\frac{{{ab}}}{{{ad}}}$.",
            f"$CB = {de} \\times \\frac{{{ab}}}{{{ad}}} = {tex(key)}$.",
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
            verify=lambda: holds(key * ad, de * ab, {}),
        )
    small = ri(rng, 2, 20)
    key = small * R(ab, ad) ** 2
    stem = f"{intro} If the area of triangle $ADE$ is {small}, what is the area of triangle $ACB$?"
    dist = ds(
        (lambda: small * R(ab, ad), "concept", "Areas scale by the square of the length ratio."),
        (lambda: small * R(ab, ad) ** 3, "wrong_formula", "Cubing is for volume."),
        (lambda: small * R(db, ad) ** 2, "misread", "Used $EB$ instead of $AB$."),
        (lambda: small * R(ab, ad) ** 2 - small, "misread", "That's the area of the trapezoid $DCBE$."),
    )
    steps = [
        f"Length ratio $\\frac{{{ab}}}{{{ad}}}$; area ratio $\\left(\\frac{{{ab}}}{{{ad}}}\\right)^2$.",
        f"Area $= {small} \\times {tex(R(ab, ad) ** 2)} = {tex(key)}$.",
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
        verify=lambda: holds(key / small, R(ab * ab, ad * ad), {}),
    )


# ---------- RTT: right triangles and trig ----------


@register(S + "RTT.PYTH")
def rtt_pyth(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "RTT.PYTH"
    if d == "easy":
        a, b, c = rng.choice(TRIPLES[:4])
        mult = ri(rng, 1, 3)
        a, b, c = a * mult, b * mult, c * mult
        key = sympy.sqrt(a**2 + b**2)
        fig = _triangle_fig(
            (0, 0),
            (b, 0),
            (0, a),
            [
                ((-0.08 * b, a / 2), str(a)),
                ((b / 2, -0.08 * a), str(b)),
                ((b / 2 + 0.05 * b, a / 2 + 0.05 * a), "?"),
            ],
            right_at="A",
        )
        stem = f"A right triangle has legs of length {a} and {b}. What is the length of the hypotenuse?"
        dist = ds(
            (lambda: R(a + b), "wrong_formula", "Added the legs; use $a^2 + b^2 = c^2$."),
            (lambda: R(a**2 + b**2), "partial_solution", "That's $c^2$."),
            (lambda: sympy.sqrt(b**2 - a**2), "sign_flip", "Subtracted the squares; that finds a leg."),
            (lambda: R(a * b, 2), "wrong_formula", "That's the area."),
        )
        steps = [f"$c^2 = {a}^2 + {b}^2 = {a * a + b * b}$.", f"$c = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            verify=lambda: key == c,
        )
    if d == "medium":
        kind = rng.choice(["30", "45"])
        h = 2 * ri(rng, 2, 10)
        if kind == "30":
            key = h * sympy.sqrt(3) / 2
            stem = f"In a $30°$-$60°$-$90°$ triangle, the hypotenuse has length {h}. What is the length of the side opposite the $60°$ angle?"
            dist = ds(
                (lambda: R(h, 2), "misread", "That's the side opposite the $30°$ angle."),
                (
                    lambda: h * sympy.sqrt(3),
                    "wrong_formula",
                    "Multiplied the hypotenuse by $\\sqrt{3}$; multiply the short leg.",
                ),
                (lambda: h * sympy.sqrt(2) / 2, "wrong_formula", "That's the 45°-45°-90° ratio."),
                (lambda: R(h, 2) * sympy.sqrt(2), "wrong_formula", "Mixed up the special-triangle ratios."),
            )
            steps = [f"Short leg $= \\frac{{{h}}}{{2}} = {h // 2}$.", f"Long leg $= {h // 2}\\sqrt{{3}}$."]
        else:
            key = h * sympy.sqrt(2) / 2
            stem = (
                f"An isosceles right triangle has a hypotenuse of length {h}. What is the length of each leg?"
            )
            dist = ds(
                (
                    lambda: h * sympy.sqrt(2),
                    "operation_swap",
                    "Multiplied by $\\sqrt{2}$; to go from hypotenuse to leg, divide.",
                ),
                (lambda: R(h, 2), "concept", "Half the hypotenuse isn't the leg here."),
                (lambda: h * sympy.sqrt(3) / 2, "wrong_formula", "That's the 30°-60°-90° ratio."),
                (lambda: R(h * h, 2), "partial_solution", "That's the leg squared."),
            )
            steps = [
                "Hypotenuse $= \\text{leg} \\times \\sqrt{2}$.",
                f"Leg $= \\frac{{{h}}}{{\\sqrt{{2}}}} = {tex(key)}$.",
            ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(key**2 + (R(h, 2) if kind == "30" else key) ** 2, h * h, {}),
        )
    a, b, c = (ri(rng, 1, 9) for _ in range(3))
    key = sympy.sqrt(a**2 + b**2 + c**2)
    stem = f"A rectangular box measures {a} by {b} by {c}. What is the length of a diagonal from one corner of the box to the opposite corner (through the interior)?"
    dist = ds(
        (lambda: sympy.sqrt(a**2 + b**2), "partial_solution", "That's the diagonal of the base only."),
        (lambda: R(a + b + c), "wrong_formula", "Added the dimensions."),
        (lambda: R(a**2 + b**2 + c**2), "partial_solution", "That's the diagonal squared."),
        (lambda: sympy.sqrt(a * b * c), "wrong_formula", "Took the root of the volume."),
    )
    steps = [
        "$d^2 = a^2 + b^2 + c^2$ (apply the Pythagorean theorem twice).",
        f"$d = \\sqrt{{{a * a + b * b + c * c}}} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds((sympy.sqrt(a**2 + b**2)) ** 2 + c**2, key**2, {}),
    )


@register(S + "RTT.TRIG")
def rtt_trig(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "RTT.TRIG"
    a, b, c = rng.choice(TRIPLES)
    if rng.random() < 0.5:
        a, b = b, a
    # Right angle at C; side a opposite A (BC), b opposite B (AC), c hypotenuse.
    A_, B_, C_ = (0.0, 0.0), (float(b), float(a)), (float(b), 0.0)
    fig = _triangle_fig(
        A_,
        B_,
        C_,
        [
            ((b + 0.06 * b, a / 2), str(a)),
            ((b / 2, -0.07 * a), str(b)),
            ((b / 2 - 0.06 * b, a / 2 + 0.05 * a), str(c)),
        ],
        right_at="C",
    )
    if d == "easy":
        key = R(a, c)
        stem = f"In right triangle $ABC$, angle $C$ is a right angle, $BC = {a}$, $AC = {b}$, and $AB = {c}$. What is the value of $\\sin A$?"
        dist = ds(
            (lambda: R(b, c), "concept", "That's $\\cos A$ (adjacent over hypotenuse)."),
            (lambda: R(a, b), "concept", "That's $\\tan A$ (opposite over adjacent)."),
            (lambda: R(c, a), "reciprocal", "Inverted the ratio."),
            (lambda: R(b, a), "reciprocal", "That's adjacent over opposite."),
        )
        steps = [f"$\\sin A = \\frac{{\\text{{opposite}}}}{{\\text{{hypotenuse}}}} = \\frac{{{a}}}{{{c}}}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            figure=fig,
            verify=lambda: holds(key, sympy.sin(sympy.atan2(a, b)), {}),
        )
    if d == "medium":
        key = R(a, b)
        stem = f"In right triangle $ABC$, angle $C$ is a right angle and $\\sin A = \\frac{{{a}}}{{{c}}}$. What is the value of $\\tan A$?"
        dist = ds(
            (lambda: R(b, a), "reciprocal", "That's $\\frac{1}{\\tan A}$."),
            (lambda: R(b, c), "concept", "That's $\\cos A$."),
            (lambda: R(a, c), "misread", "That's $\\sin A$, which was given."),
            (lambda: R(c, b), "reciprocal", "That's $\\frac{1}{\\cos A}$."),
        )
        steps = [
            f"Opposite ${a}$, hypotenuse ${c}$, so adjacent $= \\sqrt{{{c}^2 - {a}^2}} = {b}$.",
            f"$\\tan A = \\frac{{{a}}}{{{b}}}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(key, sympy.tan(sympy.asin(R(a, c))), {}),
        )
    mult = ri(rng, 2, 4)
    key = R(a * mult)
    stem = f"In right triangle $ABC$, angle $C$ is a right angle, $\\cos A = \\frac{{{b}}}{{{c}}}$, and $AB = {c * mult}$. What is the length of $BC$?"
    dist = ds(
        (lambda: R(b * mult), "concept", "That's $AC$, the side adjacent to $A$."),
        (lambda: R(c * mult * a, b), "wrong_formula", "Used $\\tan A$ with the hypotenuse."),
        (
            lambda: R(c * mult - b * mult),
            "wrong_formula",
            "Subtracted sides; use $\\sin^2 A + \\cos^2 A = 1$.",
        ),
        (lambda: R(a, c), "partial_solution", "That's $\\sin A$; multiply by the hypotenuse."),
    )
    steps = [
        f"$\\sin A = \\sqrt{{1 - \\left(\\frac{{{b}}}{{{c}}}\\right)^2}} = \\frac{{{a}}}{{{c}}}$.",
        f"$BC = AB \\sin A = {c * mult} \\times \\frac{{{a}}}{{{c}}} = {tex(key)}$.",
    ]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(key**2 + (b * mult) ** 2, (c * mult) ** 2, {}),
    )


@register(S + "RTT.COFUNC")
def rtt_cofunc(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "RTT.COFUNC"
    if d == "easy":
        a = ri(rng, 5, 85)
        key = sympy.solve(sympy.Eq(a + x, 90), x)[0]
        stem = f"If $\\sin({a}°) = \\cos(x°)$ and $0 < x < 90$, what is the value of $x$?"
        dist = ds(
            (lambda: R(a), "concept", "Sine and cosine of the same angle are only equal at 45°."),
            (
                lambda: R(180 - a),
                "wrong_formula",
                "Cofunction angles are complementary (sum to 90°), not supplementary.",
            ),
            (lambda: R(90 + a), "sign_flip", "Added 90 instead of subtracting from it."),
            (lambda: R(360 - a), "wrong_formula", "Wrong identity."),
        )
        steps = [f"$\\sin \\theta = \\cos(90° - \\theta)$, so $x = 90 - {a} = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: holds(sympy.sin(sympy.rad(a)), sympy.cos(sympy.rad(key)), {}),
        )
    if d == "medium":
        xv = ri(rng, 4, 15)
        a, c = ri(rng, 1, 4), ri(rng, 1, 4)
        b = ri(rng, -10, 20)
        dd = 90 - (a + c) * xv - b
        e1, e2 = a * x + b, c * x + dd
        while e1.subs(x, xv) <= 0 or e2.subs(x, xv) <= 0:
            b = ri(rng, -10, 20)
            dd = 90 - (a + c) * xv - b
            e1, e2 = a * x + b, c * x + dd
        key = sympy.solve(sympy.Eq(e1 + e2, 90), x)[0]
        stem = f"In a right triangle, the two acute angles measure $({tex(e1)})°$ and $({tex(e2)})°$. Equivalently, $\\sin(({tex(e1)})°) = \\cos(({tex(e2)})°)$. What is the value of $x$?"
        dist = ds(
            (
                lambda: sympy.solve(sympy.Eq(e1, e2), x)[0] if a != c else None,
                "concept",
                "Set the angles equal; cofunction angles are complementary.",
            ),
            (
                lambda: sympy.solve(sympy.Eq(e1 + e2, 180), x)[0],
                "wrong_formula",
                "Used 180°; the acute angles of a right triangle sum to 90°.",
            ),
            (lambda: e1.subs(x, key), "misread", "That's an angle measure, not $x$."),
            (lambda: -key, "sign_flip", "Sign error."),
        )
        steps = [f"$({tex(e1)}) + ({tex(e2)}) = 90$.", f"$x = {tex(key)}$."]
        return build(
            rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps, verify=lambda: key == xv
        )
    a, b, c = rng.choice(TRIPLES)
    key = R(a, c)
    stem = f"In right triangle $ABC$, angle $C$ is a right angle and $\\sin A = \\frac{{{a}}}{{{c}}}$. What is the value of $\\cos B$?"
    dist = ds(
        (lambda: R(b, c), "concept", "That's $\\cos A$ (and $\\sin B$)."),
        (lambda: R(c, a), "reciprocal", "Inverted the ratio."),
        (lambda: R(a, b), "concept", "That's $\\tan A$."),
        (lambda: R(b, a), "reciprocal", "That's $\\tan B$."),
    )
    steps = ["$A$ and $B$ are complementary, so $\\cos B = \\sin A$.", f"$\\cos B = \\frac{{{a}}}{{{c}}}$."]
    return build(
        rng,
        skill=skill,
        d=d,
        stem=stem,
        key=key,
        distractors=dist,
        steps=steps,
        verify=lambda: holds(sympy.cos(sympy.pi / 2 - sympy.asin(R(a, c))), key, {}),
    )


# ---------- CIR: circles ----------


@register(S + "CIR.ARC")
def cir_arc(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "CIR.ARC"
    r_ = ri(rng, 2, 12)
    th = rng.choice([30, 40, 45, 60, 72, 80, 90, 120, 135, 150, 210, 240, 270])
    if d == "easy":
        key = 2 * pi * r_ * R(th, 360)
        stem = f"A circle has a radius of {r_}. What is the length of an arc of the circle intercepted by a central angle of ${th}°$?"
        dist = ds(
            (lambda: pi * r_**2 * R(th, 360), "wrong_formula", "That's the sector area."),
            (lambda: pi * r_ * R(th, 360), "wrong_formula", "Circumference is $2\\pi r$, not $\\pi r$."),
            (lambda: 2 * pi * r_, "partial_solution", "That's the whole circumference."),
            (lambda: R(r_ * th), "unit_slip", "Used $s = r\\theta$ with degrees; it needs radians."),
        )
        steps = [f"Arc $= \\frac{{{th}}}{{360}} \\times 2\\pi({r_}) = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            spr=False,
            verify=lambda: abs(float(key) - r_ * math.radians(th)) < 1e-9,
        )
    if d == "medium":
        key = pi * r_**2 * R(th, 360)
        stem = f"A circle has a radius of {r_}. What is the area of a sector of the circle with a central angle of ${th}°$?"
        dist = ds(
            (lambda: 2 * pi * r_ * R(th, 360), "wrong_formula", "That's the arc length."),
            (lambda: pi * r_**2, "partial_solution", "That's the whole circle's area."),
            (lambda: pi * r_**2 * R(th, 180), "wrong_formula", "Used 180 instead of 360."),
            (lambda: pi * r_ * R(th, 360), "exponent_rule", "Forgot to square the radius."),
        )
        steps = [f"Sector $= \\frac{{{th}}}{{360}} \\times \\pi({r_})^2 = {tex(key)}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            spr=False,
            verify=lambda: abs(float(key) - 0.5 * r_**2 * math.radians(th)) < 1e-9,
        )
    s_ = r_ * R(th, 180)
    key = sympy.solve(sympy.Eq(r_ * x * pi, s_ * pi), x)[0]
    stem = f"An arc of a circle with radius {r_} has length ${tex(s_ * pi)}$. The central angle that intercepts the arc measures $a\\pi$ radians. What is the value of $a$?"
    dist = ds(
        (lambda: R(th), "unit_slip", "That's the angle in degrees."),
        (lambda: R(r_) / s_, "reciprocal", "Divided the radius by the arc length."),
        (lambda: s_ * r_, "operation_swap", "Multiplied by the radius instead of dividing."),
        (lambda: s_ / (2 * r_), "wrong_formula", "Divided by the diameter."),
    )
    steps = [
        f"$s = r\\theta$: $\\theta = \\frac{{{tex(s_ * pi)}}}{{{r_}}} = {tex(key * pi)}$.",
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
        verify=lambda: abs(float(key * pi) - math.radians(th)) < 1e-9,
    )


@register(S + "CIR.EQN")
def cir_eqn(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "CIR.EQN"
    yv = sympy.Symbol("y")
    h, kk, r_ = ri(rng, -9, 9), ri(rng, -9, 9), ri(rng, 1, 9)
    if d == "easy":
        key = R(r_)
        stem = f"In the $xy$-plane, the graph of $(x {'-' if h >= 0 else '+'} {abs(h)})^2 + (y {'-' if kk >= 0 else '+'} {abs(kk)})^2 = {r_ * r_}$ is a circle. What is the radius of the circle?"
        dist = ds(
            (lambda: R(r_ * r_), "partial_solution", "That's $r^2$."),
            (lambda: R(r_ * r_, 2), "operation_swap", "Halved instead of taking the square root."),
            (
                lambda: R(abs(h)) if abs(h) != r_ else R(2 * r_),
                "misread",
                "That's from the center coordinates." if abs(h) != r_ else "That's the diameter.",
            ),
            (lambda: R(2 * r_), "concept", "That's the diameter."),
        )
        steps = [f"$(x - h)^2 + (y - k)^2 = r^2$ with $r^2 = {r_ * r_}$, so $r = {r_}$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key**2 == r_ * r_,
        )
    expanded = sympy.expand((x - h) ** 2 + (yv - kk) ** 2 - r_**2)
    D_, E_, F_ = expanded.coeff(x, 1), expanded.coeff(yv, 1), expanded.subs({x: 0, yv: 0})
    eq = f"x^2 + y^2 {'+' if D_ >= 0 else '-'} {abs(D_)}x {'+' if E_ >= 0 else '-'} {abs(E_)}y {'+' if F_ >= 0 else '-'} {abs(F_)} = 0"
    if d == "medium":
        key = sympy.solve(sympy.diff(expanded, x), x)[0]
        stem = f"In the $xy$-plane, the graph of ${eq}$ is a circle. What is the $x$-coordinate of the center of the circle?"
        dist = ds(
            (lambda: -key, "sign_flip", "The center is at $-D/2$; the sign was dropped."),
            (lambda: R(-D_), "partial_solution", "Forgot to halve the coefficient."),
            (lambda: R(kk), "misread", "That's the $y$-coordinate of the center."),
            (lambda: R(D_), "sign_flip", "Didn't halve or change sign."),
        )
        steps = [
            f"Complete the square in $x$: $x^2 {'+' if D_ >= 0 else '-'} {abs(D_)}x = (x {'+' if D_ >= 0 else '-'} {abs(D_) // 2})^2 - {(D_ // 2) ** 2}$.",
            f"Center $x$-coordinate: ${tex(key)}$.",
        ]
        return build(
            rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps, verify=lambda: key == h
        )
    key = sympy.sqrt(R(D_**2 + E_**2, 4) - F_)
    stem = f"In the $xy$-plane, the graph of ${eq}$ is a circle. What is the radius of the circle?"
    dist = ds(
        (lambda: key**2, "partial_solution", "That's $r^2$."),
        (lambda: sympy.sqrt(R(D_**2 + E_**2, 4) + F_), "sign_flip", "Sign error moving the constant."),
        (
            lambda: sympy.sqrt(abs(F_)) if F_ else None,
            "partial_solution",
            "Forgot the terms added when completing the square.",
        ),
        (
            lambda: sympy.sqrt(D_**2 + E_**2 - F_),
            "wrong_formula",
            "Added $D^2$ and $E^2$ instead of $(D/2)^2$ and $(E/2)^2$.",
        ),
    )
    steps = [
        f"Complete the square: $(x {'-' if h >= 0 else '+'} {abs(h)})^2 + (y {'-' if kk >= 0 else '+'} {abs(kk)})^2 = {r_ * r_}$.",
        f"$r = {r_}$.",
    ]
    return build(
        rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps, verify=lambda: key == r_
    )


@register(S + "CIR.ANGLE")
def cir_angle(rng: random.Random, d: Difficulty) -> Generated:
    skill = S + "CIR.ANGLE"
    if d == "easy":
        c = 2 * ri(rng, 15, 85)
        key = sympy.solve(sympy.Eq(2 * x, c), x)[0]
        stem = f"Points $A$, $B$, and $C$ lie on a circle with center $O$. Central angle $AOB$ measures ${c}°$, and $C$ is on the major arc. What is the measure, in degrees, of inscribed angle $ACB$?"
        dist = ds(
            (lambda: R(c), "concept", "An inscribed angle is half the central angle on the same arc."),
            (lambda: R(2 * c), "operation_swap", "Doubled instead of halving."),
            (lambda: R(180 - c), "concept", "These angles aren't supplementary."),
            (lambda: R(360 - c, 2), "misread", "Used the major arc."),
        )
        steps = [f"Inscribed angle $= \\frac{{1}}{{2}} \\times {c}° = {tex(key)}°$."]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: 2 * key == c,
        )
    if d == "medium":
        a, b, c = rng.choice(TRIPLES)
        mult = ri(rng, 1, 3)
        r_, tan_len, dist_ = a * mult, b * mult, c * mult
        key = sympy.sqrt(dist_**2 - r_**2)
        stem = f"A circle has center $O$ and radius {r_}. Point $P$ is outside the circle with $OP = {dist_}$. Segment $PT$ is tangent to the circle at $T$. What is the length of $PT$?"
        dist = ds(
            (
                lambda: R(dist_ - r_),
                "concept",
                "The tangent isn't along $OP$; triangle $OTP$ has a right angle at $T$.",
            ),
            (
                lambda: sympy.sqrt(dist_**2 + r_**2),
                "wrong_formula",
                "$OP$ is the hypotenuse; subtract the squares.",
            ),
            (lambda: R(dist_ + r_), "concept", "Added the lengths."),
            (lambda: R(dist_**2 - r_**2), "partial_solution", "That's $PT^2$."),
        )
        steps = [
            "A tangent is perpendicular to the radius at the point of tangency.",
            f"$PT = \\sqrt{{{dist_}^2 - {r_}^2}} = {tex(key)}$.",
        ]
        return build(
            rng,
            skill=skill,
            d=d,
            stem=stem,
            key=key,
            distractors=dist,
            steps=steps,
            verify=lambda: key == tan_len,
        )
    xv = ri(rng, 5, 15)
    a, c = ri(rng, 1, 4), ri(rng, 1, 4)
    b = ri(rng, -5, 20)
    dd = 90 - (a + c) * xv - b
    while a * xv + b <= 5 or c * xv + dd <= 5:
        b = ri(rng, -5, 20)
        dd = 90 - (a + c) * xv - b
    e1, e2 = a * x + b, c * x + dd
    key = sympy.solve(sympy.Eq(e1 + e2 + 90, 180), x)[0]
    stem = f"Triangle $ABC$ is inscribed in a circle, and $\\overline{{AB}}$ is a diameter of the circle. Angle $A$ measures $({tex(e1)})°$ and angle $B$ measures $({tex(e2)})°$. What is the value of $x$?"
    dist = ds(
        (
            lambda: sympy.solve(sympy.Eq(e1 + e2, 180), x)[0],
            "concept",
            "Forgot that angle $C$ is a right angle (it subtends a diameter).",
        ),
        (lambda: e1.subs(x, key), "misread", "That's angle $A$, not $x$."),
        (lambda: sympy.solve(sympy.Eq(e1 + e2, 45), x)[0], "wrong_formula", "Halved the right angle."),
        (lambda: -key, "sign_flip", "Sign error."),
    )
    steps = [
        "An angle inscribed in a semicircle is $90°$, so $A + B = 90$.",
        f"$({tex(e1)}) + ({tex(e2)}) = 90$, so $x = {tex(key)}$.",
    ]
    return build(
        rng, skill=skill, d=d, stem=stem, key=key, distractors=dist, steps=steps, verify=lambda: key == xv
    )
