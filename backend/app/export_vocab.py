"""`python -m app.export_vocab [PATH]`: write every words-in-context vocab entry (keys and distractors)
from the R&W seed bank to a CSV for Anki. Default: exports/wic_vocab.csv at the repo root."""

import csv
import sys
from pathlib import Path

from app.services.questions import load_rw_seed

HEADER = ["word", "part_of_speech", "meaning_en", "meaning_ru", "example_sentence"]
DEFAULT = Path(__file__).resolve().parents[2] / "exports" / "wic_vocab.csv"


def rows() -> list[list[str]]:
    seen: dict[str, list[str]] = {}
    for item in load_rw_seed():
        for v in getattr(item, "vocab", None) or []:
            seen.setdefault(v.word.lower(), [v.word, v.pos, v.meaning_en, v.meaning_ru, v.example])
    return sorted(seen.values(), key=lambda r: r[0].lower())


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([HEADER, *rows()])
    print(f"{len(rows())} words -> {out}")


if __name__ == "__main__":
    main()
