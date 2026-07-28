"""
app/destinations.py

Destination search endpoint.

Routes
------
GET /destinations?q=paris&tag=food&continent=Europe
    Returns destinations that match any of the provided query parameters.
    All parameters are optional; omitting them returns the full catalogue.
"""
from flask import Blueprint, request, jsonify

from app.models import get_all_destinations

destinations_bp = Blueprint("destinations", __name__)


@destinations_bp.route("/destinations", methods=["GET"])
def search_destinations():
    """Search the destination catalogue.
    ---
    tags:
      - Destinations
    parameters:
      - name: q
        in: query
        type: string
        required: false
        description: Free-text search against name, country, description
      - name: tag
        in: query
        type: string
        required: false
        description: Filter by interest tag (e.g. beach)
      - name: continent
        in: query
        type: string
        required: false
        description: Filter by continent
      - name: max_cost
        in: query
        type: integer
        required: false
        description: Maximum average daily cost
    responses:
      200:
        description: List of matching destinations
      400:
        description: Invalid max_cost value
    """

    q = request.args.get("q", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower()
    continent = request.args.get("continent", "").strip().lower()
    max_cost_str = request.args.get("max_cost", "").strip()

    max_cost = None
    if max_cost_str:
        try:
            max_cost = int(max_cost_str)
        except ValueError:
            return jsonify({"error": "max_cost must be an integer"}), 400

    destinations = get_all_destinations()
    results = []

    for dest in destinations:
        # Free-text filter
        if q:
            searchable = " ".join([
                dest.get("name", ""),
                dest.get("country", ""),
                dest.get("description", ""),
            ]).lower()
            if q not in searchable:
                continue

        # Tag filter
        if tag and tag not in [t.lower() for t in dest.get("tags", [])]:
            continue

        # Continent filter
        if continent and continent != dest.get("continent", "").lower():
            continue

        # Cost filter – skip destinations that have no cost information or exceed the limit
        if max_cost is not None:
            cost = dest.get("avg_cost_per_day")
            if cost is None or cost > max_cost:
                continue

        results.append(dest)

    return jsonify(results), 200
