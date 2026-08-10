"""
Lightweight authentication — user registration, login, and project listing.

Credentials are stored as ``.credentials.json`` inside each user directory
under ``data/users/{username}/``.  No external database required.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import List, Tuple

from src.config import config

USERS_DIR = config.project_root / "data" / "users"


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username: str, password: str) -> Tuple[bool, str]:
    """Create a new user account.  Returns (success, message)."""
    if not username or not password:
        return False, "Username and password cannot be empty."

    user_dir = USERS_DIR / username
    if user_dir.exists():
        return False, "Username already exists."

    user_dir.mkdir(parents=True, exist_ok=True)
    creds_file = user_dir / ".credentials.json"
    creds_file.write_text(
        json.dumps({"username": username, "password": _hash_password(password)}),
        encoding="utf-8",
    )
    return True, f"Welcome, {username}! Account created successfully."


def authenticate_user(username: str, password: str) -> Tuple[bool, str]:
    """Verify credentials.  Returns (success, message)."""
    user_dir = USERS_DIR / username
    creds_file = user_dir / ".credentials.json"
    if not creds_file.exists():
        return False, "User does not exist."

    creds = json.loads(creds_file.read_text(encoding="utf-8"))
    if creds.get("password") == _hash_password(password):
        return True, "Login successful."
    return False, "Invalid password."


def list_user_projects(username: str) -> List[str]:
    """Return a sorted list of project directory names for *username*."""
    projects_dir = USERS_DIR / username / "projects"
    if not projects_dir.exists():
        return []
    return sorted(p.name for p in projects_dir.iterdir() if p.is_dir())


def create_project(username: str, project_name: str) -> Tuple[bool, str]:
    """Create a new project directory for *username*.  Returns (success, message)."""
    if not project_name.strip():
        return False, "Project name cannot be empty."

    safe = project_name.strip().replace(" ", "_").lower()
    proj_dir = USERS_DIR / username / "projects" / safe
    if proj_dir.exists():
        return False, f"Project '{safe}' already exists."

    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "documents").mkdir(exist_ok=True)
    (proj_dir / "notes").mkdir(exist_ok=True)
    (proj_dir / "graphs").mkdir(exist_ok=True)
    return True, safe
