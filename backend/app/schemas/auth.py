from datetime import date, timedelta

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class Goals(BaseModel):
    test_date: date
    target_total: int = Field(ge=400, le=1600, multiple_of=10)
    target_math: int | None = Field(default=None, ge=200, le=800, multiple_of=10)
    target_rw: int | None = Field(default=None, ge=200, le=800, multiple_of=10)

    @field_validator("test_date")
    @classmethod
    def _upcoming(cls, v: date) -> date:
        today = date.today()
        # A day of slack for time zones ahead of the server's.
        if not today - timedelta(days=1) <= v <= today + timedelta(days=3 * 365):
            raise ValueError("Pick an upcoming test date")
        return v

    @model_validator(mode="after")
    def _fits_total(self) -> "Goals":
        if (self.target_math or 0) + (self.target_rw or 0) > self.target_total:
            raise ValueError("Section goals add up to more than the total goal")
        return self


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)


class RegisterIn(Credentials, Goals):
    pass


class UserOut(BaseModel):
    id: int
    email: str
    test_date: date | None
    target_total: int | None
    target_math: int | None
    target_rw: int | None
    section_targets: dict[str, int] | None


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
