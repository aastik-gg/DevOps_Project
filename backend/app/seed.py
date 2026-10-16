"""Load demo equipment so a fresh environment has something to show.

Idempotent: does nothing if the inventory already has items.
Run with:  python -m app.seed
"""

from datetime import timedelta

from sqlalchemy import func, select

from . import db as db_module
from .models import Item, Loan, utcnow

DEMO_ITEMS = [
    ("Rigol DS1054Z Oscilloscope", "Measurement", "MS-001", "Bench 2", "GOOD"),
    ("Fluke 117 Multimeter", "Measurement", "MS-002", "Bench 1", "FAIR"),
    ("Hakko FX-888D Soldering Station", "Tools", "TL-001", "Bench 3", "GOOD"),
    ("Raspberry Pi 5 Kit", "Computing", "CP-001", "Cabinet A", "GOOD"),
    ("Arduino Mega Starter Kit", "Electronics", "EL-001", "Cabinet A", "GOOD"),
    ("Sony A7 III + 28-70mm", "Cameras", "CM-001", "Media room", "GOOD"),
    ("Rode NT-USB Microphone", "Audio", "AU-001", "Media room", "FAIR"),
    ("Bench Power Supply 30V/5A", "Electronics", "EL-002", "Bench 2", "NEEDS_REPAIR"),
    ("Prusa MK4 Filament Spool Set", "Tools", "TL-002", "Store room", "GOOD"),
    ("DJI RS 3 Gimbal", "Cameras", "CM-002", "Media room", "GOOD"),
]

DEMO_LOANS = [
    # (asset_tag, borrower, purpose, borrowed_days_ago, loan_days)
    ("CM-001", "Ananya (Media club)", "Fest promo shoot", 2, 5),
    ("CP-001", "Kabir (CSE, 3rd yr)", "IoT mini project", 10, 7),  # overdue
    ("MS-001", "Dr. Mehta", "Signals lab session", 1, 3),
]


def seed() -> int:
    with db_module.SessionLocal() as db:
        if db.scalar(select(func.count(Item.id))):
            return 0
        items = {}
        for name, category, tag, location, condition in DEMO_ITEMS:
            items[tag] = Item(name=name, category=category, asset_tag=tag, location=location, condition=condition)
            db.add(items[tag])
        now = utcnow()
        for tag, borrower, purpose, ago, days in DEMO_LOANS:
            start = now - timedelta(days=ago)
            due = start + timedelta(days=days)
            db.add(Loan(item=items[tag], borrower=borrower, purpose=purpose, borrowed_at=start, due_at=due))
        db.commit()
        return len(DEMO_ITEMS)


if __name__ == "__main__":
    created = seed()
    print(f"Seeded {created} demo items" if created else "Inventory not empty; skipping seed")
