from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Item
from ..schemas import ItemCreate, ItemOut, ItemStatus, ItemUpdate
from ..services import load_items

router = APIRouter(prefix="/api/items", tags=["items"])


def get_item_or_404(item_id: int, db: Session) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("", response_model=list[ItemOut])
def list_items(
    status_filter: ItemStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=120, description="Search name, tag or category"),
    db: Session = Depends(get_db),
):
    items = load_items(db)
    if status_filter:
        items = [item for item in items if item.status == status_filter]
    if q:
        needle = q.lower()
        items = [i for i in items if needle in f"{i.name} {i.asset_tag} {i.category}".lower()]
    return items


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return get_item_or_404(item_id, db)


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["asset_tag"] = data["asset_tag"].upper()
    if db.scalar(select(Item.id).where(Item.asset_tag == data["asset_tag"])):
        raise HTTPException(status_code=409, detail=f"Asset tag {data['asset_tag']} is already in use")
    item = Item(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    item = get_item_or_404(item_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = get_item_or_404(item_id, db)
    if item.active_loan is not None:
        raise HTTPException(status_code=409, detail="Item is on loan; return it before deleting")
    db.delete(item)
    db.commit()
