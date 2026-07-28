def test_register_success(client):
    """Registration with valid data returns 201."""
    response = client.post("/register", json={
        "username": "alice",
        "password": "secret123",
        "preferences": ["beach"]
    })
    assert response.status_code == 201


def test_register_duplicate(client):
    """Registering the same username twice returns 409."""
    client.post("/register", json={
        "username": "alice",
        "password": "secret123",
        "preferences": []
    })
    response = client.post("/register", json={
        "username": "alice",
        "password": "other456",
        "preferences": []
    })
    assert response.status_code == 409


def test_register_missing_fields(client):
    """Registration without username or password returns 400."""
    response = client.post("/register", json={
        "username": "",
        "password": "secret123"
    })
    assert response.status_code == 400


def test_login_success(client):
    """Login with correct credentials returns 200 and a token."""
    client.post("/register", json={
        "username": "alice",
        "password": "secret123",
        "preferences": []
    })
    response = client.post("/login", json={
        "username": "alice",
        "password": "secret123"
    })
    assert response.status_code == 200
    assert "token" in response.get_json()


def test_login_wrong_password(client):
    """Login with wrong password returns 401."""
    client.post("/register", json={
        "username": "alice",
        "password": "secret123",
        "preferences": []
    })
    response = client.post("/login", json={
        "username": "alice",
        "password": "wrongpassword"
    })
    assert response.status_code == 401