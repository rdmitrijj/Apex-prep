from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.models import OfficialScore
from app.services import exam as ex

router = APIRouter(prefix="/official-scores", tags=["scores"])


class OfficialIn(BaseModel):
    taken_on: date
    kind: Literal["practice", "real"] = "practice"
    label: str = Field(default="", max_length=100)
    rw: int = Field(ge=200, le=800)
    math: int = Field(ge=200, le=800)

    @field_validator("rw", "math")
    @classmethod
    def _step(cls, v: int) -> int:
        if v % 10:
            raise ValueError("section scores come in steps of 10")
        return v

    @field_validator("taken_on")
    @classmethod
    def _past(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("that date is in the future")
        return v


class OfficialOut(BaseModel):
    id: int
    taken_on: date
    kind: str
    label: str
    rw: int
    math: int
    paired_exam: dict[str, int]  # section -> in-app exam used for calibration


class SectionCalibration(BaseModel):
    pairs: int
    intercept: float
    slope: float


class OfficialList(BaseModel):
    scores: list[OfficialOut]
    calibration: dict[str, SectionCalibration]
    window_days: int


@router.get("", response_model=OfficialList)
async def list_scores(db: DB, user: CurrentUser) -> OfficialList:
    cal = await ex.calibration(db, user.id)
    rows = (
        await db.scalars(
            select(OfficialScore)
            .where(OfficialScore.user_id == user.id)
            .order_by(OfficialScore.taken_on.desc(), OfficialScore.id.desc())
        )
    ).all()
    return OfficialList(
        scores=[
            OfficialOut(
                id=o.id,
                taken_on=o.taken_on,
                kind=o.kind,
                label=o.label,
                rw=o.rw,
                math=o.math,
                paired_exam=cal.matches.get(o.id, {}),
            )
            for o in rows
        ],
        calibration={
            s: SectionCalibration(pairs=sc.n, intercept=round(sc.intercept, 1), slope=round(sc.slope, 1))
            for s, sc in cal.scales.items()
        },
        window_days=ex.PAIR_WINDOW_DAYS,
    )


@router.post("", status_code=201)
async def add_score(body: OfficialIn, db: DB, user: CurrentUser) -> dict[str, int]:
    o = OfficialScore(user_id=user.id, **body.model_dump())
    db.add(o)
    await db.flush()
    await ex.rescore(db, user.id)
    await db.commit()
    return {"id": o.id}


@router.delete("/{score_id}", status_code=204)
async def delete_score(score_id: int, db: DB, user: CurrentUser) -> None:
    o = await db.get(OfficialScore, score_id)
    if o is None or o.user_id != user.id:
        raise HTTPException(404, "Score not found")
    await db.delete(o)
    await db.flush()
    await ex.rescore(db, user.id)
    await db.commit()
