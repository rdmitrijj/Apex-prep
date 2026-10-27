from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.engine.goals import section_targets

Json = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    test_date: Mapped[date | None] = mapped_column(Date)
    target_total: Mapped[int | None] = mapped_column(SmallInteger)
    target_math: Mapped[int | None] = mapped_column(SmallInteger)  # optional section minimums
    target_rw: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = _now()

    @property
    def section_targets(self) -> dict[str, int] | None:
        if self.target_total is None:
            return None
        return section_targets(self.target_total, self.target_math, self.target_rw)


class Skill(Base):
    """Node of the taxonomy tree (section/domain/skill/subskill). Loaded from seed/taxonomy.json."""

    __tablename__ = "skills"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("skills.id"))
    name: Mapped[str] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(16))
    section: Mapped[str] = mapped_column(String(8))
    weight: Mapped[float] = mapped_column(Float)


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("format IN ('mc','spr')", name="format"),
        CheckConstraint("difficulty IN ('easy','medium','hard')", name="difficulty"),
        CheckConstraint("source IN ('generator','llm','seed')", name="source"),
        CheckConstraint("status IN ('active','quarantined')", name="status"),
        Index("ix_questions_pick", "skill_id", "difficulty", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    format: Mapped[str] = mapped_column(String(3))
    difficulty: Mapped[str] = mapped_column(String(6))
    difficulty_rating: Mapped[float] = mapped_column(Float)
    content: Mapped[dict[str, Any]] = mapped_column(Json)
    source: Mapped[str] = mapped_column(String(9))
    status: Mapped[str] = mapped_column(String(11), server_default="active")
    # sha256 of normalized stem+passage; blocks exact duplicates. Near-dupes are filtered in the pipeline.
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # Stable key of a seed-file item; the seed updates the row in place when the item is edited.
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = _now()


class ExamSession(Base):
    __tablename__ = "exam_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    difficulty_setting: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(12), server_default="in_progress")
    rw_score: Mapped[int | None] = mapped_column(SmallInteger)
    math_score: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = _now()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExamModule(Base):
    __tablename__ = "exam_modules"
    __table_args__ = (UniqueConstraint("session_id", "section", "stage"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id", ondelete="CASCADE"))
    section: Mapped[str] = mapped_column(String(4))
    stage: Mapped[int] = mapped_column(SmallInteger)
    route: Mapped[str | None] = mapped_column(String(6))  # stage 2 only: 'easier' | 'harder'
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExamItem(Base):
    """Question slot within an exam module (fixed order; pretest slots are unscored)."""

    __tablename__ = "exam_items"
    __table_args__ = (UniqueConstraint("module_id", "position"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("exam_modules.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    pretest: Mapped[bool] = mapped_column(Boolean, server_default="false")


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (
        CheckConstraint("mode IN ('exam','drill','training')", name="mode"),
        Index("ix_responses_user_time", "user_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    mode: Mapped[str] = mapped_column(String(8))
    exam_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_items.id", ondelete="CASCADE"), unique=True
    )
    answer: Mapped[str | None] = mapped_column(String(16))
    correct: Mapped[bool | None] = mapped_column(Boolean)
    time_ms: Mapped[int] = mapped_column(Integer, server_default="0")
    flagged: Mapped[bool] = mapped_column(Boolean, server_default="false")
    eliminated: Mapped[list[str]] = mapped_column(Json, server_default="[]")
    miss_reason: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = _now()


class SkillMastery(Base):
    __tablename__ = "skill_mastery"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    rating: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MasteryHistory(Base):
    __tablename__ = "mastery_history"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    rating: Mapped[float] = mapped_column(Float)
    response_id: Mapped[int | None] = mapped_column(ForeignKey("responses.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _now()
    __table_args__ = (Index("ix_mastery_history_user_skill", "user_id", "skill_id", "created_at"),)


class ReviewSchedule(Base):
    __tablename__ = "review_schedule"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    interval_days: Mapped[int] = mapped_column(SmallInteger)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    plan: Mapped[dict[str, Any]] = mapped_column(Json)
    created_at: Mapped[datetime] = _now()


class QuestionReport(Base):
    __tablename__ = "question_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()


class OfficialScore(Base):
    """Scores from official practice tests / real sittings; ground truth for score calibration."""

    __tablename__ = "official_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    taken_on: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(8))  # 'practice' | 'real'
    label: Mapped[str] = mapped_column(String(100), server_default="")
    rw: Mapped[int] = mapped_column(SmallInteger)
    math: Mapped[int] = mapped_column(SmallInteger)
    __table_args__ = (
        CheckConstraint("rw BETWEEN 200 AND 800 AND rw % 10 = 0", name="rw_range"),
        CheckConstraint("math BETWEEN 200 AND 800 AND math % 10 = 0", name="math_range"),
    )


class ImportedMistake(Base):
    """A miss from an official practice test, entered by hand. Holds a paraphrase and the lesson,
    never the official item's text. Counts as an exam miss in weaknesses and has its own review
    schedule; it retires once its twin questions are all answered right on two separate days."""

    __tablename__ = "imported_mistakes"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id"),
        CheckConstraint("result IN ('incorrect','omitted')", name="result"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    external_id: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(120))
    taken_on: Mapped[date] = mapped_column(Date)
    module: Mapped[int] = mapped_column(SmallInteger)
    question_number: Mapped[int] = mapped_column(SmallInteger)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    difficulty: Mapped[str] = mapped_column(String(6))
    result: Mapped[str] = mapped_column(String(9))
    my_answer: Mapped[str | None] = mapped_column(String(120))
    correct_answer: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    lesson: Mapped[str] = mapped_column(Text)
    where_to_review: Mapped[str] = mapped_column(String(200))
    miss_reason: Mapped[str | None] = mapped_column(String(16))
    linked_ids: Mapped[list[str]] = mapped_column(Json, server_default="[]")  # twin questions.external_id
    interval_days: Mapped[int | None] = mapped_column(SmallInteger)  # None until the first review
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
