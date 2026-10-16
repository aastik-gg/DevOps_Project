from app.seed import DEMO_ITEMS, seed


def test_seed_is_idempotent(client):
    assert seed() == len(DEMO_ITEMS)
    assert seed() == 0
    stats = client.get("/api/stats").json()
    assert stats["total_items"] == len(DEMO_ITEMS)
    assert stats["overdue"] == 1
    assert stats["maintenance"] == 1
