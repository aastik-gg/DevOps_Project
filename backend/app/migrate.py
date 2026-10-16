"""Apply Alembic migrations safely from many pods at once.

Every backend pod runs this as an initContainer. A Postgres advisory lock makes
replicas take turns, so only the first one actually migrates; the rest find the
schema already at head and continue. Run with:  python -m app.migrate [--seed]
"""

import argparse
import sys
import time
from pathlib import Path

from sqlalchemy import text

from alembic import command
from alembic.config import Config

from . import db as db_module

LOCK_ID = 0x6E41_1007  # arbitrary, constant across releases
BACKEND_DIR = Path(__file__).resolve().parent.parent


def wait_for_database(timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            with db_module.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:
            if time.monotonic() > deadline:
                raise SystemExit(f"database not reachable after {timeout:.0f}s: {exc}") from exc
            print("waiting for database...", flush=True)
            time.sleep(2)


def migrate(seed: bool) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    use_lock = db_module.engine.dialect.name == "postgresql"

    with db_module.engine.connect() as conn:
        if use_lock:
            conn.execute(text("SELECT pg_advisory_lock(:id)"), {"id": LOCK_ID})
        try:
            command.upgrade(cfg, "head")
            if seed:
                from .seed import seed as run_seed

                created = run_seed()
                print(f"seeded {created} demo items" if created else "inventory not empty; skipping seed", flush=True)
        finally:
            if use_lock:
                conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="store_true", help="load demo data into an empty inventory")
    parser.add_argument("--wait", type=float, default=120, help="seconds to wait for the database")
    args = parser.parse_args(argv)
    wait_for_database(args.wait)
    migrate(args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
