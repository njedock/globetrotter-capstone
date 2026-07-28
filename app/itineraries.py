"""
app/itineraries.py

Create and list itineraries for the authenticated user.

Routes
------
POST /itineraries – create a new itinerary
GET  /itineraries – list all itineraries for the logged-in user

Both routes require a valid JWT in the Authorization header.
"""
import uuid
import datetime

from flask import Blueprint, request, jsonify

from app.auth import get_current_user
from app.models import get_itineraries_for_user, save_itinerary

itineraries_bp = Blueprint("itineraries", __name__)


@itineraries_bp.route("/itineraries", methods=["POST"])
def create_itinerary():
    """Create a new itinerary.
    ---
    tags:
      - Itineraries
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: "Bearer <JWT token>"
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - destinations
          properties:
            title:
              type: string
              example: Beach Escape
            destinations:
              type: array
              items:
                type: string
              example: ["Kribi", "Bali"]
            start_date:
              type: string
              example: "2026-08-01"
            end_date:
              type: string
              example: "2026-08-07"
            notes:
              type: string
              example: Pack sunscreen
    responses:
      201:
        description: Itinerary created
      400:
        description: Validation error
      401:
        description: Authentication required
    """
    username = get_current_user(request)
    if not username:
        return jsonify({"error": "authentication required"}), 401

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    destinations = data.get("destinations", [])

    if not title:
        return jsonify({"error": "title is required"}), 400

    if not isinstance(destinations, list):
        return jsonify({"error": "destinations must be a list"}), 400

    if len(destinations) == 0:
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


@itineraries_bp.route("/itineraries", methods=["GET"])
def list_itineraries():
    """List all itineraries for the logged-in user.
    ---
    tags:
      - Itineraries
    parameters:
      - name: Authorization
        in: header
        type: string
        required: true
        description: "Bearer <JWT token>"
    responses:
      200:
        description: List of user itineraries
      401:
        description: Authentication required
    """
    username = get_current_user(request)
    if not username:
        return jsonify({"error": "authentication required"}), 401

    itineraries = get_itineraries_for_user(username)
    return jsonify(itineraries), 200