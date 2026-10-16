from datetime import UTC, datetime, timedelta

from app.models import Loan


def checkout(client, item_id, **overrides):
    payload = {"item_id": item_id, "borrower": "Priya (ECE)", "purpose": "Robotics demo", "days": 3} | overrides
    return client.post("/api/loans", json=payload)


def test_checkout_marks_item_on_loan(client, make_item):
    item = make_item()
    response = checkout(client, item["id"])
    assert response.status_code == 201
    loan = response.json()
    assert loan["item_name"] == "Oscilloscope"
    assert loan["overdue"] is False

    refreshed = client.get(f"/api/items/{item['id']}").json()
    assert refreshed["status"] == "ON_LOAN"
    assert refreshed["active_loan"]["borrower"] == "Priya (ECE)"


def test_cannot_double_checkout(client, make_item):
    item = make_item()
    assert checkout(client, item["id"]).status_code == 201
    assert checkout(client, item["id"], borrower="Someone else").status_code == 409


def test_cannot_checkout_item_in_maintenance(client, make_item):
    item = make_item(condition="NEEDS_REPAIR")
    assert checkout(client, item["id"]).status_code == 409


def test_loan_length_is_capped(client, make_item):
    item = make_item()
    assert checkout(client, item["id"], days=90).status_code == 422


def test_return_frees_the_item(client, make_item):
    item = make_item()
    loan = checkout(client, item["id"]).json()

    returned = client.post(f"/api/loans/{loan['id']}/return")
    assert returned.status_code == 200
    assert returned.json()["returned_at"] is not None
    assert client.get(f"/api/items/{item['id']}").json()["status"] == "AVAILABLE"
    assert client.post(f"/api/loans/{loan['id']}/return").status_code == 409


def test_cannot_delete_item_on_loan(client, make_item):
    item = make_item()
    checkout(client, item["id"])
    assert client.delete(f"/api/items/{item['id']}").status_code == 409


def test_overdue_loans_show_in_stats(client, make_item, db_session):
    item = make_item()
    loan = checkout(client, item["id"]).json()
    db_session.get(Loan, loan["id"]).due_at = datetime.now(UTC) - timedelta(days=2)
    db_session.commit()

    assert client.get(f"/api/items/{item['id']}").json()["status"] == "OVERDUE"
    stats = client.get("/api/stats").json()
    assert stats["overdue"] == 1
    assert stats["utilisation_pct"] == 100.0


def test_active_filter_on_loan_list(client, make_item):
    first = make_item(asset_tag="A-1")
    second = make_item(asset_tag="A-2")
    loan = checkout(client, first["id"]).json()
    checkout(client, second["id"])
    client.post(f"/api/loans/{loan['id']}/return")

    assert len(client.get("/api/loans", params={"active": "true"}).json()) == 1
    assert len(client.get("/api/loans", params={"active": "false"}).json()) == 1
    assert len(client.get("/api/loans").json()) == 2


def test_stats_on_empty_inventory(client):
    stats = client.get("/api/stats").json()
    assert stats["total_items"] == 0
    assert stats["utilisation_pct"] == 0.0
