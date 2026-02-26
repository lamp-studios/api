import json
import os
import re

MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")


def _sanitize_username(username):
    """Sanitize username to prevent path traversal."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', username)


def _path(username):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    return os.path.join(MEMORY_DIR, f"{_sanitize_username(username)}.json")


def load_history(username):
    path = _path(username)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def save_history(username, messages):
    with open(_path(username), "w") as f:
        json.dump(messages, f)
