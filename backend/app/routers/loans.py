from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..db import get_db
from ..metrics import CHECKOUTS, RETURNS
from ..models import Item, Loan, utcnow
from ..schemas import LoanCreate, LoanOut

router = APIRouter(prefix="/api/loans", tags=["loans"])


@router.get("", response_model=list[LoanOut])
def list_loans(
    active: bool | None = Query(default=None, description="true = still out, false = returned"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = select(Loan).options(selectinload(Loan.item)).order_by(Loan.id.desc()).limit(limit)
    if active is True:
        query = query.where(Loan.returned_at.is_(None))
    elif active is False:
        query = query.where(Loan.returned_at.is_not(None))
    return db.scalars(query).all()


@router.post("", response_model=LoanOut, status_code=status.HTTP_201_CREATED)
def check_out(payload: LoanCreate, db: Session = Depends(get_db)):
    if payload.days > settings.max_loan_days:
        raise HTTPException(status_code=422, detail=f"Loans are limited to {settings.max_loan_days} days")
    item = db.get(Item, payload.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.status != "AVAILABLE":
        raise HTTPException(status_code=409, detail=f"{item.name} is not available ({item.status})")

    now = utcnow()
    loan = Loan(
        item=item,
        borrower=payload.borrower.strip(),
        purpose=payload.purpose.strip(),
        borrowed_at=now,
        due_at=now + timedelta(days=payload.days),
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    CHECKOUTS.labels(category=item.category).inc()
    return loan


@router.post("/{loan_id}/return", response_model=LoanOut)
def return_item(loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.returned_at is not None:
        raise HTTPException(status_code=409, detail="Loan was already returned")
    late = loan.overdue
    loan.returned_at = utcnow()
    db.commit()
    db.refresh(loan)
    RETURNS.labels(late=str(late).lower()).inc()
    return loan
