def test_get_all_destinations(client):
    """GET /destinations returns the full catalogue."""
    response = client.get("/destinations")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2  # Kribi and Zermatt from conftest


def test_filter_by_tag(client):
    """Filtering by tag returns only matching destinations."""
    response = client.get("/destinations?tag=beach")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Kribi"