import pytest
import os
import json
import tempfile
import shutil
from app import create_app


@pytest.fixture
def app():
    """Create a test app with a temporary data directory."""
    # Create a temporary directory for test data
    test_data_dir = tempfile.mkdtemp()

    # Create a test destinations file
    destinations = [
        {
            "id": "d001",
            "name": "Kribi",
            "country": "Cameroon",
            "continent": "Africa",
            "description": "Golden beaches and fresh seafood.",
            "tags": ["beach", "food", "nature"],
            "avg_cost_per_day": 45
        },
        {
            "id": "d002",
            "name": "Zermatt",
            "country": "Switzerland",
            "continent": "Europe",
            "description": "Alpine skiing and mountain views.",
            "tags": ["ski", "mountain"],
            "avg_cost_per_day": 200
        }
    ]

    with open(os.path.join(test_data_dir, "destinations.json"), "w") as f:
        json.dump(destinations, f)

    # Point the app at the test data directory
    import app.models as models
    original_data_dir = models.DATA_DIR
    models.DATA_DIR = test_data_dir
    models.USERS_FILE = os.path.join(test_data_dir, "users.json")
    models.ITINERARIES_FILE = os.path.join(test_data_dir, "itineraries.json")
    models.DESTINATIONS_FILE = os.path.join(test_data_dir, "destinations.json")

    application = create_app()
    application.config["TESTING"] = True
    application.config["SECRET_KEY"] = "test-secret-key"

    yield application

    # Cleanup: restore original paths and delete temp files
    models.DATA_DIR = original_data_dir
    models.USERS_FILE = os.path.join(original_data_dir, "users.json")
    models.ITINERARIES_FILE = os.path.join(original_data_dir, "itineraries.json")
    models.DESTINATIONS_FILE = os.path.join(original_data_dir, "destinations.json")
    shutil.rmtree(test_data_dir)


@pytest.fixture
def client(app):
    """A test client that sends requests without a real server."""
    return app.test_client()


@pytest.fixture
def auth_header(client):
    """Register a user, login, and return the Authorization header."""
    # Register
    client.post("/register", json={
        "username": "testuser",
        "password": "testpass123",
        "preferences": ["beach", "food"]
    })
    # Login
    response = client.post("/login", json={
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}