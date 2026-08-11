"""
User-scoped API key manager — save, load, resolve, and mask personal keys
stored inside ``data/users/{uid}/settings.json``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional


def get_user_settings_path(user_id: str) -> Path:
    """Absolute path to the user's ``settings.json``."""
    user_dir = Path("data/users") / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir / "settings.json"


def load_user_keys(user_id: str) -> Dict[str, str]:
    """Load saved API keys for *user_id*."""
    if not user_id:
        return {}
    sf = get_user_settings_path(user_id)
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8")).get("api_keys", {})
        except Exception:
            return {}
    return {}


def save_user_keys(user_id: str, keys: Dict[str, str]) -> str:
    """Merge *keys* into the user's settings and persist.

    Empty values are treated as removals.  Values starting with ``"••••"``
    (masked) are ignored so the UI doesn't overwrite with placeholders.
    """
    if not user_id:
        return "Error: No active user session."

    sf = get_user_settings_path(user_id)
    data: dict = {}
    if sf.exists():
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    current = data.get("api_keys", {})
    for k, v in keys.items():
        if v and v.strip() and not v.startswith("••••"):
            current[k] = v.strip()
        elif v == "":
            current.pop(k, None)

    data["api_keys"] = current
    sf.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return "✅ API keys updated successfully!"


def resolve_api_key(user_id: str, key_name: str) -> str:
    """Resolve a key: user-saved → system env → empty string."""
    if user_id:
        uk = load_user_keys(user_id)
        if uk.get(key_name):
            return uk[key_name]
    return os.getenv(key_name, "")


def mask_key(key_val: str) -> str:
    """Return a masked version safe for UI display."""
    if not key_val:
        return ""
    if len(key_val) <= 8:
        return "••••••••"
    return key_val[:4] + "••••••••" + key_val[-4:]
