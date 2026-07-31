"""
Recommendation Service — owns destination search and personalised recommendations.
Calls User Service over HTTP to get user preferences.
"""
import json
import os
import urllib.error
import urllib.request

import jwt
from flask import Flask, request as flask_request, jsonify

from models import get_all_destinations

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-change-in-prod"
)

# URL of User Service — configurable via environment variable
USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://localhost:5001")


def get_current_user():
    """Extract username from JWT token."""
    auth_header = flask_request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


@app.route("/destinations", methods=["GET"])
def search_destinations():
    """Search the destination catalogue (public, no auth required)."""
    q = flask_request.args.get("q", "").strip().lower()
    tag = flask_request.args.get("tag", "").strip().lower()
    continent = flask_request.args.get("continent", "").strip().lower()
    max_cost_str = flask_request.args.get("max_cost", "").strip()

    max_cost = None
    if max_cost_str:
        try:
            max_cost = int(max_cost_str)
        except ValueError:
            return jsonify({"error": "max_cost must be an integer"}), 400

    destinations = get_all_destinations()
    results = []

    for dest in destinations:
        if q:
            searchable = " ".join([
                dest.get("name", ""),
                dest.get("country", ""),
                dest.get("description", ""),
            ]).lower()
            if q not in searchable:
                continue

        if tag and tag not in [t.lower() for t in dest.get("tags", [])]:
            continue

        if continent and continent != dest.get("continent", "").lower():
            continue

        if max_cost is not None:
            cost = dest.get("avg_cost_per_day")
            if cost is None or cost > max_cost:
                continue

        results.append(dest)

    return jsonify(results), 200


@app.route("/recommendations", methods=["GET"])
def get_recommendations():
    """Get personalised recommendations by matching user preferences to destination tags.

    THIS IS THE INTER-SERVICE CALL:
    Instead of importing get_user_by_username() (which lives in User Service),
    we make an HTTP request to User Service's /users/<username> endpoint.
    """
    username = get_current_user()
    if not username:
        return jsonify({"error": "authentication required"}), 401

    # ---- THE INTER-SERVICE HTTP CALL ----
    try:
        with urllib.request.urlopen(
            f"{USER_SERVICE_URL}/users/{username}", timeout=5
        ) as response:
            if response.status != 200:
                return jsonify({"error": "could not fetch user preferences"}), 502
            user_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return jsonify({"error": "could not fetch user preferences"}), 502
    except urllib.error.URLError:
        return jsonify({"error": "user service unavailable"}), 503
    # ---- END INTER-SERVICE CALL ----

    preferences = [p.lower() for p in user_data.get("preferences", [])]

    try:
        limit = int(flask_request.args.get("limit", 5))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    destinations = get_all_destinations()

    scored = []
    for dest in destinations:
        dest_tags = [t.lower() for t in dest.get("tags", [])]
        score = sum(1 for pref in preferences if pref in dest_tags)
        scored.append((score, dest))

    scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))

    results = []
    for score, dest in scored[:limit]:
        entry = dict(dest)
        entry["match_score"] = score
        results.append(entry)

    return jsonify(results), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    return jsonify({"status": "healthy", "service": "recommendation-service"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port)