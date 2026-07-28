def test_create_itinerary(client, auth_header):
    """Creating an itinerary with valid data returns 201."""
    response = client.post("/itineraries",
        json={
            "title": "Beach Trip",
            "destinations": ["Kribi"],
            "start_date": "2026-08-01",
            "end_date": "2026-08-07"
        },
        headers=auth_header
    )
    assert response.status_code == 201
    assert response.get_json()["title"] == "Beach Trip"


def test_create_itinerary_no_title(client, auth_header):
    """Creating an itinerary without a title returns 400."""
    response = client.post("/itineraries",
        json={"destinations": ["Kribi"]},
        headers=auth_header
    )
    assert response.status_code == 400


def test_list_itineraries(client, auth_header):
    """Listing itineraries after creating one returns it."""
    client.post("/itineraries",
        json={"title": "Trip", "destinations": ["Kribi"]},
        headers=auth_header
    )
    response = client.get("/itineraries", headers=auth_header)
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_itineraries_requires_auth(client):
    """Accessing itineraries without a token returns 401."""
    response = client.get("/itineraries")
    assert response.status_code == 401