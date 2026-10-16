from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Condition = Literal["GOOD", "FAIR", "NEEDS_REPAIR"]
ItemStatus = Literal["AVAILABLE", "ON_LOAN", "OVERDUE", "MAINTENANCE"]


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="General", min_length=1, max_length=60)
    asset_tag: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9-]+$")
    location: str = Field(default="Main lab", max_length=120)
    condition: Condition = "GOOD"
    notes: str = ""


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    location: str | None = Field(default=None, max_length=120)
    condition: Condition | None = None
    notes: str | None = None


class LoanCreate(BaseModel):
    item_id: int
    borrower: str = Field(min_length=1, max_length=120)
    purpose: str = Field(default="", max_length=200)
    days: int = Field(default=7, ge=1)


class LoanOut(BaseModel):
    id: int
    item_id: int
    item_name: str
    borrower: str
    purpose: str
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    overdue: bool

    model_config = ConfigDict(from_attributes=True)


class ItemOut(BaseModel):
    id: int
    name: str
    category: str
    asset_tag: str
    location: str
    condition: Condition
    notes: str
    status: ItemStatus
    active_loan: LoanOut | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryCount(BaseModel):
    category: str
    count: int


class StatsOut(BaseModel):
    total_items: int
    available: int
    on_loan: int
    overdue: int
    maintenance: int
    loans_last_7_days: int
    utilisation_pct: float
    categories: list[CategoryCount]
