from datetime import datetime

from pydantic import BaseModel


class UsageLedgerOut(BaseModel):
    id: str
    kind: str
    units: int
    cost_units: int
    ref_type: str | None = None
    ref_id: str | None = None
    created_at: datetime


class UsageKindTotal(BaseModel):
    kind: str
    units: int
    cost_units: int
    events: int


class UsageSummaryOut(BaseModel):
    units: int
    cost_units: int
    events: int
    by_kind: list[UsageKindTotal]
