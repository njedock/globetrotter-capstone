"""
Data access layer for User Service.
Only this file touches users.json.
"""
import os
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _read_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.loads(f.read())


def _write_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(json.dumps(data, indent=2))


def get_all_users():
    return _read_json(USERS_FILE)


def get_user_by_username(username):
    users = get_all_users()
    for user in users:
        if user["username"] == username:
            return user
    return None


def save_user(user):
    users = get_all_users()
    users.append(user)
    _write_json(USERS_FILE, users)