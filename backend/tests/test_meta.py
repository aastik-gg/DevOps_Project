def test_health_is_up(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_root_identifies_service(client):
    body = client.get("/").json()
    assert body["service"] == "GearLoop API"
    assert body["docs"] == "/docs"


def test_ready_when_schema_exists(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_metrics_exposes_http_and_inventory_gauges(client, make_item):
    make_item()
    scope = make_item(asset_tag="LAB-002")
    client.post("/api/loans", json={"item_id": scope["id"], "borrower": "Asha", "days": 2})
    client.get("/api/items")
    text = client.get("/metrics").text
    assert "http_requests_total" in text
    assert 'gearloop_items{status="AVAILABLE"} 1.0' in text
    assert 'gearloop_items{status="ON_LOAN"} 1.0' in text
    assert 'gearloop_checkouts_last_24h{category="Measurement"} 1.0' in text
