"""
Data access layer for Itinerary Service.
Only this file touches itineraries.json.
"""
import os
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ITINERARIES_FILE = os.path.join(DATA_DIR, "itineraries.json")


def _read_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.loads(f.read())


def _write_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(json.dumps(data, indent=2))


def get_itineraries_for_user(username):
    itineraries = _read_json(ITINERARIES_FILE)
    return [it for it in itineraries if it["username"] == username]


def save_itinerary(itinerary):
    itineraries = _read_json(ITINERARIES_FILE)
    itineraries.append(itinerary)
    _write_json(ITINERARIES_FILE, itineraries)