from collections import Counter
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .models import Item, Loan, utcnow

STATUSES = ("AVAILABLE", "ON_LOAN", "OVERDUE", "MAINTENANCE")


def load_items(db: Session):
    return db.scalars(select(Item).options(selectinload(Item.loans)).order_by(Item.name)).all()


def inventory_snapshot(db: Session) -> dict[str, int]:
    counts = Counter(item.status for item in load_items(db))
    return {status: counts.get(status, 0) for status in STATUSES}


def recent_checkouts_by_category(db: Session, hours: int = 24) -> dict[str, int]:
    since = utcnow() - timedelta(hours=hours)
    query = (
        select(Item.category, func.count(Loan.id))
        .join(Loan.item)
        .where(Loan.borrowed_at >= since)
        .group_by(Item.category)
    )
    rows = db.execute(query).all()
    return {category: count for category, count in rows}
