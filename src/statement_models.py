from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class BuildEvent(BaseModel):
    occurred_at: datetime
    project: str = Field(min_length=1)
    status: Literal["succeeded", "failed", "cancelled"]
    duration_seconds: int = Field(ge=0)


class ReleaseOperation(BaseModel):
    occurred_at: datetime
    project: str = Field(min_length=1)
    environment: Literal["preview", "staging", "production"]
    status: Literal["succeeded", "failed", "rolled_back"]


class DeveloperDiagnostic(BaseModel):
    occurred_at: datetime
    project: str = Field(min_length=1)
    severity: Literal["debug", "info", "warning", "error"]
    code: str = Field(min_length=1)


class MonthlyStatementRequest(BaseModel):
    customer_name: str = Field(min_length=1)
    recipient: str = Field(min_length=3)
    period_start: date
    period_end: date
    builds: list[BuildEvent] = Field(default_factory=list)
    releases: list[ReleaseOperation] = Field(default_factory=list)
    diagnostics: list[DeveloperDiagnostic] = Field(default_factory=list)

    @model_validator(mode="after")
    def period_is_ordered(self) -> "MonthlyStatementRequest":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class StatementTotals(BaseModel):
    builds: int
    build_minutes: int
    releases: int
    production_releases: int
    actionable_diagnostics: int


class StatementDelivery(BaseModel):
    message_id: str
    pdf_url: str
    totals: StatementTotals
