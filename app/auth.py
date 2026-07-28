"""
app/auth.py

User registration, login, and JWT handling.

Routes
------
POST /register  – create a new user account
POST /login     – authenticate and return a JWT token
"""
import uuid
import datetime

import jwt
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from app.models import get_user_by_username, save_user

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Helper – JWT utilities
# ---------------------------------------------------------------------------

def create_token(username: str, secret: str) -> str:
    """Return a signed JWT for *username* valid for 24 hours."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + datetime.timedelta(hours=24),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict:
    """Decode and verify *token*. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, secret, algorithms=["HS256"])


def get_current_user(request_obj) -> str | None:
    """Extract and validate the JWT from the Authorization header.

    Returns the username (subject claim) or None if the token is missing /
    invalid.
    """
    auth_header = request_obj.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_token(token, current_app.config["SECRET_KEY"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: alice
            password:
              type: string
              example: s3cr3t
            preferences:
              type: array
              items:
                type: string
              example: ["beach", "food"]
    responses:
      201:
        description: User registered successfully
      400:
        description: Validation error
      409:
        description: Username already exists
    """
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


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return a JWT token.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: alice
            password:
              type: string
              example: s3cr3t
    responses:
      200:
        description: Login successful, returns JWT token
      400:
        description: Missing credentials
      401:
        description: Invalid credentials
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    token = create_token(username, current_app.config["SECRET_KEY"])
    return jsonify({"token": token}), 200