"""Rules-based weekly study plan counting down to test day.

- More than 3 weeks out ("build"): one full practice exam a week, on Saturday at test time.
- Final 3 weeks ("sharpen"): two exams a week: Math-only on Hard (Wednesday) + full exam (Saturday).
- No exams in the last 3 days ("taper"); the day before the test is a rest day.
- No exam taken yet: the first open day is a diagnostic full exam.
- Other days: weakness training plus a topic drill on one focus skill, rotating through the top
  weaknesses (already Math-weighted); Sundays review the Mistake Notebook and due SRS skills.
"""

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote

TEST_DATE = date(2026, 12, 5)
FULL_EXAM_MINUTES = 134 + 10
WED, SAT, SUN = 2, 5, 6


@dataclass(frozen=True)
class Focus:
    skill_id: str
    name: str
    section: str
    difficulty: str  # what the drill should target (from the skill's mastery)


@dataclass(frozen=True)
class Task:
    id: str
    kind: str  # exam | training | drill | notebook | rest | test
    title: str
    detail: str
    minutes: int
    link: str


def phase(days_left: int) -> str:
    return "build" if days_left > 21 else "sharpen" if days_left > 3 else "taper"


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _exam(d: date, days_left: int, diagnostic: bool) -> Task | None:
    if diagnostic:
        return Task(
            f"{d}-exam",
            "exam",
            "Diagnostic: full practice exam",
            "Official-level, in one sitting. Everything else in the plan keys off this result.",
            FULL_EXAM_MINUTES,
            "/exam",
        )
    if days_left <= 3:
        return None
    if d.weekday() == SAT:
        return Task(
            f"{d}-exam",
            "exam",
            "Full practice exam",
            "Official-level, starting around 8:00 like the real test, with the 10-minute break.",
            FULL_EXAM_MINUTES,
            "/exam",
        )
    if days_left <= 21 and d.weekday() == WED:
        return Task(
            f"{d}-exam",
            "exam",
            "Math-only exam on Hard",
            "Two timed Math modules; Hard keeps the 700 target in reach.",
            70,
            "/exam",
        )
    return None


def week_plan(week_start: date, today: date, focus: list[Focus], has_exam: bool) -> dict[str, Any]:
    days: list[dict[str, Any]] = []
    diagnostic_day = None
    if not has_exam:
        first = max(today, week_start)
        if (TEST_DATE - first).days >= 2 and first < week_start + timedelta(days=7):
            diagnostic_day = first
    for i in range(7):
        d = week_start + timedelta(days=i)
        left = (TEST_DATE - d).days
        if left < 0:
            break
        tasks: list[Task] = []
        f = focus[i % len(focus)] if focus else None
        exam = _exam(d, left, d == diagnostic_day)
        if left == 0:
            tasks.append(
                Task(
                    f"{d}-test",
                    "test",
                    "Test day",
                    "Bring photo ID and a charged device with the testing app; arrive early; eat breakfast.",
                    0,
                    "/",
                )
            )
        elif left == 1:
            tasks.append(
                Task(
                    f"{d}-rest",
                    "rest",
                    "Rest day",
                    "At most 20 minutes skimming your Mistake Notebook. Pack your bag and sleep early.",
                    20,
                    "/mistakes",
                )
            )
        elif exam:
            tasks.append(exam)
            tasks.append(
                Task(
                    f"{d}-notebook",
                    "notebook",
                    "Review the exam",
                    "Read every miss's solution and tag why you missed it.",
                    30,
                    "/mistakes",
                )
            )
        elif d.weekday() == SUN or left <= 3:
            tasks.append(
                Task(
                    f"{d}-notebook",
                    "notebook",
                    "Mistake Notebook review",
                    "Re-solve this week's misses without looking, then retry similar questions.",
                    30,
                    "/mistakes",
                )
            )
            tasks.append(
                Task(
                    f"{d}-training",
                    "training",
                    "Spaced-repetition reviews",
                    "Weakness training picks up the skills that are due for review.",
                    20,
                    "/training",
                )
            )
        else:
            long = phase(left) == "sharpen"
            tasks.append(
                Task(
                    f"{d}-training",
                    "training",
                    "Weakness training",
                    "Adaptive questions on your weakest skills" + (f", led by {f.name}." if f else "."),
                    45 if long else 35,
                    "/training",
                )
            )
            if f:
                tasks.append(
                    Task(
                        f"{d}-drill",
                        "drill",
                        f"Topic drill: {f.name}",
                        f"10 {f.difficulty} questions with worked solutions.",
                        25 if long else 20,
                        f"/drill?skills={quote(f.skill_id)}&difficulty={f.difficulty}&count=10",
                    )
                )
        days.append({"date": d.isoformat(), "days_left": left, "tasks": [asdict(t) for t in tasks]})
    return {
        "week_start": week_start.isoformat(),
        "phase": phase((TEST_DATE - max(today, week_start)).days),
        "focus": [asdict(f) for f in focus],
        "days": days,
    }
