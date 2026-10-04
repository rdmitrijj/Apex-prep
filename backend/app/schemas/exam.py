from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.question import Difficulty, Letter, QuestionOut

Section = Literal["RW", "MATH"]


class ExamCreate(BaseModel):
    difficulty: Literal["official", "hard", "brutal"] = "official"
    sections: list[Section] = Field(default=["RW", "MATH"], min_length=1, max_length=2)

    @field_validator("sections")
    @classmethod
    def _official_order(cls, v: list[Section]) -> list[Section]:
        return [s for s in ("RW", "MATH") if s in v]  # type: ignore[misc]


class ItemSave(BaseModel):
    answer: str | None = Field(default=None, max_length=16)
    flagged: bool = False
    eliminated: list[Letter] = Field(default_factory=list, max_length=4)
    time_ms: int = Field(default=0, ge=0, le=3_600_000)  # total time spent on this item so far


class ExamItemOut(BaseModel):
    id: int
    position: int
    question: QuestionOut
    answer: str | None
    flagged: bool
    eliminated: list[str]
    time_ms: int


class ModuleOut(BaseModel):
    id: int
    section: Section
    stage: int
    index: int  # 1-based position among the exam's modules
    started: bool
    remaining_ms: int | None
    items: list[ExamItemOut]  # empty until the module is started


class ExamState(BaseModel):
    id: int
    status: str
    difficulty: str
    sections: list[Section]
    total_modules: int
    module: ModuleOut | None
    break_remaining_ms: int | None


class ExamSummary(BaseModel):
    id: int
    status: str
    difficulty: str
    sections: list[Section]
    created_at: datetime
    completed_at: datetime | None
    rw_score: int | None
    math_score: int | None


class ReviewItem(BaseModel):
    module: str  # e.g. "Math · Module 2 (harder)"
    section: Section
    position: int
    pretest: bool
    question: QuestionOut
    difficulty: Difficulty
    answer: str | None
    correct: bool
    key: str
    time_ms: int
    flagged: bool
    explanation: list[str]
    rationales: dict[str, str]


class BreakdownRow(BaseModel):
    id: str
    name: str
    level: str
    section: Section
    correct: int
    total: int


class ExamResults(ExamSummary):
    breakdown: list[BreakdownRow]
    items: list[ReviewItem]
