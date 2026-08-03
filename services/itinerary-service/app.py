"""
Itinerary Service — owns trip creation and listing.
Runs independently on its own port.
"""
import os
import uuid
import datetime

import jwt
from flask import Flask, request, jsonify

from models import get_itineraries_for_user, save_itinerary

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-change-in-prod"
)


def get_current_user():
    """Extract username from JWT token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


@app.route("/itineraries", methods=["POST"])
def create_itinerary():
    """Create a new itinerary for the authenticated user."""
    username = get_current_user()
    if not username:
        return jsonify({"error": "authentication required"}), 401

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    destinations = data.get("destinations", [])

    if not title:
        return jsonify({"error": "title is required"}), 400

    if not isinstance(destinations, list) or len(destinations) == 0:
        return jsonify({"error": "at least one destination is required"}), 400

    start_date = data.get("start_date", "").strip()
    end_date = data.get("end_date", "").strip()

    if start_date and end_date and start_date > end_date:
        return jsonify({"error": "start_date must be before end_date"}), 400

    itinerary = {
        "id": str(uuid.uuid4()),
        "username": username,
        "title": title,
        "destinations": destinations,
        "start_date": start_date,
        "end_date": end_date,
        "notes": data.get("notes", ""),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    save_itinerary(itinerary)
    return jsonify(itinerary), 201


@app.route("/itineraries", methods=["GET"])
def list_itineraries():
    """List itineraries for the authenticated user."""
    username = get_current_user()
    if not username:
        return jsonify({"error": "authentication required"}), 401

    itineraries = get_itineraries_for_user(username)
    return jsonify(itineraries), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    return jsonify({"status": "healthy", "service": "itinerary-service"}), 200



@app.route("/itineraries/<itinerary_id>/share", methods=["POST"])
def share_itinerary(itinerary_id):
    """Share an itinerary with another user."""
    username = get_current_user()
    if not username:
        return jsonify({"error": "authentication required"}), 401

    data = request.get_json(silent=True) or {}
    share_with = data.get("share_with", "").strip()

    if not share_with:
        return jsonify({"error": "share_with username is required"}), 400

    itineraries = get_itineraries_for_user(username)
    target = None
    for it in itineraries:
        if it["id"] == itinerary_id:
            target = it
            break

    if not target:
        return jsonify({"error": "itinerary not found"}), 404

    # Add shared_with list if not present
    if "shared_with" not in target:
        target["shared_with"] = []

    if share_with not in target["shared_with"]:
        target["shared_with"].append(share_with)

    # Update the itinerary in storage
    from models import _read_json, _write_json, ITINERARIES_FILE
    all_itineraries = _read_json(ITINERARIES_FILE)
    for i, it in enumerate(all_itineraries):
        if it["id"] == itinerary_id:
            all_itineraries[i] = target
            break
    _write_json(ITINERARIES_FILE, all_itineraries)

    return jsonify({
        "message": f"itinerary shared with {share_with}",
        "itinerary": target
    }), 200


@app.route("/itineraries/shared", methods=["GET"])
def list_shared_itineraries():
    """List itineraries shared with the current user."""
    username = get_current_user()
    if not username:
        return jsonify({"error": "authentication required"}), 401

    from models import _read_json, ITINERARIES_FILE
    all_itineraries = _read_json(ITINERARIES_FILE)
    shared = [it for it in all_itineraries if username in it.get("shared_with", [])]
    return jsonify(shared), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port)