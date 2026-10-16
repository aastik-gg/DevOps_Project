def test_create_and_get_item(client, make_item):
    item = make_item(asset_tag="cam-07", name="Sony A7 III", category="Cameras")
    assert item["asset_tag"] == "CAM-07"  # tags are normalised to upper case
    assert item["status"] == "AVAILABLE"
    assert item["active_loan"] is None

    fetched = client.get(f"/api/items/{item['id']}").json()
    assert fetched["name"] == "Sony A7 III"


def test_duplicate_asset_tag_is_rejected(client, make_item):
    make_item(asset_tag="LAB-001")
    response = client.post("/api/items", json={"name": "Another scope", "asset_tag": "lab-001"})
    assert response.status_code == 409


def test_invalid_payload_is_rejected(client):
    response = client.post("/api/items", json={"name": "", "asset_tag": "has spaces"})
    assert response.status_code == 422


def test_update_condition_moves_item_to_maintenance(client, make_item):
    item = make_item()
    response = client.put(f"/api/items/{item['id']}", json={"condition": "NEEDS_REPAIR", "location": "Repair shelf"})
    assert response.status_code == 200
    assert response.json()["status"] == "MAINTENANCE"
    assert response.json()["location"] == "Repair shelf"


def test_list_filters_by_status_and_search(client, make_item):
    make_item(name="Soldering station", category="Tools", asset_tag="TL-1")
    make_item(name="Multimeter", category="Measurement", asset_tag="MS-1", condition="NEEDS_REPAIR")

    assert [i["name"] for i in client.get("/api/items", params={"status": "MAINTENANCE"}).json()] == ["Multimeter"]
    assert [i["name"] for i in client.get("/api/items", params={"q": "tools"}).json()] == ["Soldering station"]


def test_delete_item(client, make_item):
    item = make_item()
    assert client.delete(f"/api/items/{item['id']}").status_code == 204
    assert client.get(f"/api/items/{item['id']}").status_code == 404


def test_missing_item_returns_404(client):
    assert client.get("/api/items/999").status_code == 404
    assert client.put("/api/items/999", json={"name": "x"}).status_code == 404
