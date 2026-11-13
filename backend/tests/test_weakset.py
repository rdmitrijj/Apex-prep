from datetime import date

from app.engine.weakset import readiness, status

D1, D2 = date(2026, 11, 13), date(2026, 11, 14)


def test_mastery_needs_80_percent_of_last_8_on_two_days() -> None:
    assert not status([(D1, True)] * 8).mastered  # one day only
    two_days = [(D1, True)] * 4 + [(D2, True)] * 3 + [(D2, False)]
    s = status(two_days)
    assert s.mastered and s.recent_correct == 7 and s.days == 2 and s.progress == 1.0
    six = [(D1, True)] * 4 + [(D2, True)] * 2 + [(D2, False)] * 2  # 75%
    assert not status(six).mastered
    assert not status([(D1, True)] * 3 + [(D2, True)] * 4).mastered  # only 7 answers


def test_only_the_last_8_answers_count() -> None:
    early_misses = [(D1, False)] * 10 + [(D1, True)] * 4 + [(D2, True)] * 4
    s = status(early_misses)
    assert s.mastered and s.answered == 18 and s.recent_total == 8
    # a late miss streak un-masters it
    assert not status(early_misses + [(D2, False)] * 2).mastered


def test_progress_stays_below_one_until_mastered() -> None:
    assert status([]).progress == 0.0
    assert status([(D1, True)] * 8).progress < 1.0
    assert readiness([1.0, 0.5]) == 0.75 and readiness([]) == 0.0
