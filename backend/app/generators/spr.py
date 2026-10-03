"""Student-produced response (SPR) grading, per the official entry rules (docs/SAT_SPEC.md §4)."""

import re
from collections.abc import Iterable
from fractions import Fraction
from math import floor, trunc

_ENTRY = re.compile(r"^-?(\d+|\d+\.\d*|\.\d+|\d+/\d+)$")


def char_limit(entry: str) -> int:
    return 6 if entry.startswith("-") else 5


def is_valid_entry(entry: str) -> bool:
    """Shape check only: digits, one '.', or one '/', optional leading '-', within the char limit."""
    return bool(_ENTRY.match(entry)) and len(entry) <= char_limit(entry)


def _truncate(x: Fraction, places: int) -> Fraction:
    scale = 10**places
    return Fraction(trunc(x * scale), scale)


def _round(x: Fraction, places: int) -> Fraction:
    scale = 10**places
    sign = -1 if x < 0 else 1
    return Fraction(sign * floor(abs(x) * scale + Fraction(1, 2)), scale)


def is_correct(entry: str, answers: Iterable[Fraction]) -> bool:
    """Exact (any equivalent fraction/decimal), or a decimal that fills every available character
    and equals the answer truncated or rounded at that precision. Short imprecise decimals fail."""
    s = entry.strip()
    if not is_valid_entry(s):
        return False
    answers = list(answers)
    if "/" in s:
        num, den = s.lstrip("-").split("/")
        if int(den) == 0:
            return False
        value = Fraction(int(num), int(den)) * (-1 if s.startswith("-") else 1)
        return value in answers
    value = Fraction(s)
    if value in answers:
        return True
    if len(s) != char_limit(s) or "." not in s:
        return False
    places = len(s.split(".")[1])
    return any(value in (_truncate(a, places), _round(a, places)) for a in answers)


def canonical_entry(x: Fraction) -> str:
    """An accepted entry for x: the reduced fraction if it fits, else a full-width rounded decimal."""
    s = str(x)  # Fraction prints as "p/q" or "n"
    if len(s) <= char_limit(s):
        return s
    limit = char_limit("-" if x < 0 else "")
    whole = str(abs(trunc(x)))
    if whole == "0":
        whole = ""  # ".6667" is allowed and keeps one more digit
    places = limit - len(whole) - 1 - (1 if x < 0 else 0)
    if places < 1:
        return str(round(x))
    r = _round(x, places)
    digits = f"{abs(r):.{places}f}"
    if digits.startswith("0."):
        digits = digits[1:]
    return ("-" if x < 0 else "") + digits
