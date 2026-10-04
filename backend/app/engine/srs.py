"""Spaced repetition per sub-skill: review after 1, 3, 7, then every 14 days.

A correct answer on or after the due date moves to the next interval; practising early doesn't
extend it. A miss resets to 1 day whenever it happens.
"""

from datetime import date, timedelta

INTERVALS = (1, 3, 7, 14)


def next_review(interval: int | None, due: date | None, today: date, correct: bool) -> tuple[int, date]:
    """(new interval in days, new due date) after answering a question on this skill today."""
    if not correct:
        return 1, today + timedelta(days=1)
    if interval is None or due is None:
        return INTERVALS[0], today + timedelta(days=INTERVALS[0])
    if today < due:
        return interval, due
    nxt = next((i for i in INTERVALS if i > interval), INTERVALS[-1])
    return nxt, today + timedelta(days=nxt)
