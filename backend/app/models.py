from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite drops tzinfo on read; Postgres keeps it. Normalise both to aware UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (CheckConstraint("condition IN ('GOOD', 'FAIR', 'NEEDS_REPAIR')", name="ck_items_condition"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="General")
    asset_tag: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    location: Mapped[str] = mapped_column(String(120), nullable=False, default="Main lab")
    condition: Mapped[str] = mapped_column(String(20), nullable=False, default="GOOD")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    loans: Mapped[list["Loan"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="Loan.id.desc()"
    )

    @property
    def active_loan(self) -> "Loan | None":
        return next((loan for loan in self.loans if loan.returned_at is None), None)

    @property
    def status(self) -> str:
        loan = self.active_loan
        if loan is not None:
            return "OVERDUE" if loan.overdue else "ON_LOAN"
        if self.condition == "NEEDS_REPAIR":
            return "MAINTENANCE"
        return "AVAILABLE"


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        Index(
            "uq_loans_one_open_per_item",
            "item_id",
            unique=True,
            postgresql_where=text("returned_at IS NULL"),
            sqlite_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    borrower: Mapped[str] = mapped_column(String(120), nullable=False)
    purpose: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    borrowed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    item: Mapped[Item] = relationship(back_populates="loans")

    @property
    def item_name(self) -> str:
        return self.item.name

    @property
    def overdue(self) -> bool:
        return self.returned_at is None and as_utc(self.due_at) < utcnow()
