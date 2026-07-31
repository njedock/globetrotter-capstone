"""
Data access layer for Recommendation Service.
Only this file touches destinations.json.
"""
import os
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DESTINATIONS_FILE = os.path.join(DATA_DIR, "destinations.json")


def _read_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.loads(f.read())


def get_all_destinations():
    return _read_json(DESTINATIONS_FILE)