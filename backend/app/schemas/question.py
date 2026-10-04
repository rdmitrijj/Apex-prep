from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Letter = Literal["A", "B", "C", "D"]
Difficulty = Literal["easy", "medium", "hard"]


class Table(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["table"]
    title: str | None = None
    header: list[str] = Field(min_length=2, max_length=8)
    rows: list[list[str]] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def _rect(self) -> "Table":
        if any(len(r) != len(self.header) for r in self.rows):
            raise ValueError("every table row needs one cell per header column")
        return self


class Series(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    values: list[float]


class Bars(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["bars"]
    title: str | None = None
    labels: list[str] = Field(min_length=2, max_length=12)
    values: list[float] | None = None
    series: list[Series] | None = None  # grouped bars
    xlabel: str = ""
    ylabel: str = ""

    @model_validator(mode="after")
    def _shape(self) -> "Bars":
        groups = [self.values] if self.values is not None else [s.values for s in self.series or []]
        if not groups or any(len(g) != len(self.labels) for g in groups):
            raise ValueError("bars need values (or series) with one value per label")
        return self


class Line(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["line"]
    title: str | None = None
    x: list[float] = Field(min_length=2, max_length=20)
    series: list[Series] = Field(min_length=1, max_length=4)
    xlabel: str = ""
    ylabel: str = ""

    @model_validator(mode="after")
    def _shape(self) -> "Line":
        if any(len(s.values) != len(self.x) for s in self.series):
            raise ValueError("each line series needs one value per x")
        return self


RWFigure = Table | Bars | Line


class Rationales(BaseModel):
    """Why each choice is right or wrong (explicit fields, not a dict, for structured outputs)."""

    model_config = ConfigDict(extra="forbid")
    A: str = Field(min_length=3)
    B: str = Field(min_length=3)
    C: str = Field(min_length=3)
    D: str = Field(min_length=3)


class RWItem(BaseModel):
    """A Reading & Writing item: the on-disk seed format and the LLM pipeline's output schema."""

    model_config = ConfigDict(extra="forbid")
    skill: str = Field(pattern=r"^RW\.[A-Z]+\.[A-Z]+\.[A-Z]+$")
    difficulty: Difficulty
    passage: str = Field(min_length=20, max_length=1400)
    passage2: str | None = Field(default=None, max_length=1000)  # cross-text items: "Text 2"
    notes: list[str] | None = Field(default=None, max_length=8)  # rhetorical synthesis bullets
    figure: RWFigure | None = None
    stem: str = Field(min_length=10, max_length=600)
    choices: list[str] = Field(min_length=4, max_length=4)
    answer: Letter
    explanation: str = Field(min_length=20)
    rationales: Rationales

    @field_validator("choices")
    @classmethod
    def _distinct(cls, v: list[str]) -> list[str]:
        if len({c.strip().lower() for c in v}) != 4 or any(not c.strip() for c in v):
            raise ValueError("choices must be 4 distinct non-empty strings")
        return v

    @model_validator(mode="after")
    def _consistent(self) -> "RWItem":
        if self.skill.startswith("RW.EOI.RS") and not self.notes:
            raise ValueError("rhetorical synthesis items need notes")
        if self.skill.startswith("RW.CAS.CTC") and not self.passage2:
            raise ValueError("cross-text items need passage2")
        if self.skill.startswith("RW.INI.COEQ") and self.figure is None:
            raise ValueError("quantitative evidence items need a figure")
        if self.skill.startswith("RW.CAS.TSP.FUNCTION") and "<u>" not in self.passage:
            raise ValueError("function items need an <u>underlined</u> portion")
        return self


class QuestionOut(BaseModel):
    """What the client sees before answering: no key, explanation, or rationales."""

    id: int
    skill_id: str
    skill_name: str
    difficulty: Difficulty
    format: Literal["mc", "spr"]
    stem: str
    choices: list[str] | None
    passage: str | None = None
    passage2: str | None = None
    notes: list[str] | None = None
    figure: dict[str, Any] | None = None


class AnswerIn(BaseModel):
    question_id: int
    answer: str = Field(min_length=1, max_length=16)
    time_ms: int = Field(ge=0, le=3_600_000)
    mode: Literal["drill", "training"] = "drill"


class Feedback(BaseModel):
    response_id: int
    correct: bool
    answer: str  # MC letter, or an accepted SPR entry
    explanation: list[str]
    rationales: dict[str, str]


class NextIn(BaseModel):
    skill_ids: list[str] = Field(min_length=1, max_length=100)
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    exclude_ids: list[int] = Field(default_factory=list, max_length=200)


class ReportIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class SkillNode(BaseModel):
    id: str
    parent_id: str | None
    name: str
    level: str
    section: str
    weight: float
    generated: bool  # unlimited items via a math generator
    available: int  # active stored questions
    attempts: int
    correct: int
