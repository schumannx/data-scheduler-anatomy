from datetime import datetime

from croniter import croniter
from pydantic import BaseModel, Field, field_validator, model_validator


class ScheduleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    cron: str = Field(..., description="5-field cron, e.g. 0 * * * *")
    next_run: datetime
    start_date: datetime
    end_date: datetime

    @field_validator("cron")
    @classmethod
    def cron_must_parse(cls, v: str) -> str:
        try:
            croniter(v, datetime(2000, 1, 1))
        except Exception as e:
            raise ValueError(f"Invalid cron expression: {e}") from e
        return v

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ScheduleOut(BaseModel):
    id: str
    name: str
    cron: str
    next_run: datetime
    start_date: datetime
    end_date: datetime
