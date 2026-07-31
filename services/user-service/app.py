"""
User Service — owns user registration, login, and profile lookup.
Runs independently on its own port.
"""
import os
import uuid
import datetime

import jwt
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from models import get_user_by_username, save_user

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-change-in-prod"
)


# ---- JWT helpers ----

def create_token(username):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


def get_current_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


# ---- Routes ----

@app.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    preferences = data.get("preferences", [])

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if len(username) < 3:
        return jsonify({"error": "username must be at least 3 characters"}), 400

    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400

    if not isinstance(preferences, list):
        return jsonify({"error": "preferences must be a list"}), 400

    if get_user_by_username(username):
        return jsonify({"error": "username already exists"}), 409

    user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "password_hash": generate_password_hash(password),
        "preferences": preferences,
    }
    save_user(user)
    return jsonify({"message": "user registered successfully", "username": username}), 201


@app.route("/login", methods=["POST"])
def login():
    """Authenticate and return a JWT."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    token = create_token(username)
    return jsonify({"token": token}), 200


@app.route("/users/<username>", methods=["GET"])
def get_user_profile(username):
    """Return a user's public profile (used by other services).
    
    This endpoint is NEW — it didn't exist in Phase 1 because
    other code could just call get_user_by_username() directly.
    Now that Recommendation Service is a separate app, it needs
    an HTTP endpoint to ask for a user's preferences.
    """
    user = get_user_by_username(username)
    if not user:
        return jsonify({"error": "user not found"}), 404

    # Never expose the password hash to other services
    return jsonify({
        "username": user["username"],
        "preferences": user["preferences"],
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check — used by Docker/gateway to verify the service is alive."""
    return jsonify({"status": "healthy", "service": "user-service"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)