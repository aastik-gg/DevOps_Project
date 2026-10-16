from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Item

STATUSES = ("AVAILABLE", "ON_LOAN", "OVERDUE", "MAINTENANCE")


def load_items(db: Session):
    return db.scalars(select(Item).options(selectinload(Item.loans)).order_by(Item.name)).all()


def inventory_snapshot(db: Session) -> dict[str, int]:
    counts = Counter(item.status for item in load_items(db))
    return {status: counts.get(status, 0) for status in STATUSES}
