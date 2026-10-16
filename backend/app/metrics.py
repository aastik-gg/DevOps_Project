"""Business metrics exported next to the HTTP metrics on /metrics.

The gauges are computed when Prometheus scrapes, so they always match the database
instead of drifting with in-process counters across replicas.
"""

from prometheus_client import Counter
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY, Collector

from . import db as db_module
from .services import inventory_snapshot, recent_checkouts_by_category

CHECKOUTS = Counter("gearloop_checkouts_total", "Items checked out", ["category"])
RETURNS = Counter("gearloop_returns_total", "Items returned", ["late"])


class InventoryCollector(Collector):
    def collect(self):
        try:
            with db_module.SessionLocal() as db:
                snapshot = inventory_snapshot(db)
                recent = recent_checkouts_by_category(db, hours=24)
        except Exception:
            # A scrape must never fail just because the DB is briefly unreachable;
            # /ready already reports that.
            return
        items = GaugeMetricFamily("gearloop_items", "Items by current status", labels=["status"])
        for status, count in snapshot.items():
            items.add_metric([status], count)
        yield items

        # Read from the DB rather than per-pod counters: identical on every replica and survives restarts.
        checkouts = GaugeMetricFamily(
            "gearloop_checkouts_last_24h", "Loans started in the last 24 hours", labels=["category"]
        )
        for category, count in recent.items():
            checkouts.add_metric([category], count)
        yield checkouts


_registered = False


def register_inventory_collector() -> None:
    global _registered
    if not _registered:
        REGISTRY.register(InventoryCollector())
        _registered = True
