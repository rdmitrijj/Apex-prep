"""Per-user score goals: section targets and how much each section's weaknesses count."""

MAX_BOOST = 1.3


def section_targets(total: int, math: int | None, rw: int | None) -> dict[str, int]:
    """Section targets from the goals; a section without its own minimum gets what the total leaves it."""
    if math is None:
        math = total - rw if rw is not None else -(-total // 20) * 10  # half, rounded up to a multiple of 10
    if rw is None:
        rw = total - math
    return {"MATH": max(200, min(800, math)), "RW": max(200, min(800, rw))}


def section_boost(targets: dict[str, int] | None, current: dict[str, int] | None = None) -> dict[str, float]:
    """Weakness multiplier per section, up to 1.3x for the section that needs more work.

    With a current (latest official) score, "more work" is the bigger gap to the section's target;
    otherwise it's the higher target. A 50-point difference earns the full boost.
    """
    if targets is None:
        gap = 0
    elif current is None:
        gap = targets["MATH"] - targets["RW"]
    else:
        gap = (targets["MATH"] - current["MATH"]) - (targets["RW"] - current["RW"])
    return {
        "MATH": 1 + min(MAX_BOOST - 1, 0.006 * max(0, gap)),
        "RW": 1 + min(MAX_BOOST - 1, 0.006 * max(0, -gap)),
    }


def priority(targets: dict[str, int] | None, current: dict[str, int] | None = None) -> str:
    """The section the goals lean on (Math on a tie)."""
    b = section_boost(targets, current)
    return "RW" if b["RW"] > b["MATH"] else "MATH"
