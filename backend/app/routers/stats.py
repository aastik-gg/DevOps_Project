from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Loan, utcnow
from ..schemas import CategoryCount, StatsOut
from ..services import load_items

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    items = load_items(db)
    by_status = Counter(item.status for item in items)
    by_category = Counter(item.category for item in items)
    week_ago = utcnow() - timedelta(days=7)
    recent = db.scalar(select(func.count(Loan.id)).where(Loan.borrowed_at >= week_ago)) or 0

    out = by_status["ON_LOAN"] + by_status["OVERDUE"]
    return StatsOut(
        total_items=len(items),
        available=by_status["AVAILABLE"],
        on_loan=by_status["ON_LOAN"],
        overdue=by_status["OVERDUE"],
        maintenance=by_status["MAINTENANCE"],
        loans_last_7_days=recent,
        utilisation_pct=round(100 * out / len(items), 1) if items else 0.0,
        categories=[CategoryCount(category=c, count=n) for c, n in by_category.most_common()],
    )
