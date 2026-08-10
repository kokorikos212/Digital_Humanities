"""
Linux-like file manager — directory listing and safe deletion within project sandbox.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from src.config import resolve_project_dir


def list_project_directory(
    user_id: str, project_id: str, rel_path: str = ""
) -> pd.DataFrame:
    """List files and folders inside the project sandbox as a DataFrame.

    Columns: ``Name``, ``Type``, ``Size``, ``Relative Path``.
    """
    if not user_id or not project_id:
        return pd.DataFrame(columns=["Name", "Type", "Size", "Relative Path"])

    project_root = resolve_project_dir(user_id, project_id).resolve()
    target_dir = (project_root / rel_path).resolve()

    if not str(target_dir).startswith(str(project_root)) or not target_dir.exists():
        target_dir = project_root

    items = []
    for entry in sorted(target_dir.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
        rel = str(entry.relative_to(project_root))
        is_dir = entry.is_dir()
        try:
            size = "<DIR>" if is_dir else f"{entry.stat().st_size:,} B"
        except OSError:
            size = "—"
        items.append({
            "Name": entry.name,
            "Type": "Folder" if is_dir else (entry.suffix or "File"),
            "Size": size,
            "Relative Path": rel,
        })

    if not items:
        return pd.DataFrame(columns=["Name", "Type", "Size", "Relative Path"])
    return pd.DataFrame(items)


def delete_project_item(user_id: str, project_id: str, rel_path: str) -> str:
    """Safely delete a file or directory within the project sandbox."""
    if not user_id or not project_id or not rel_path.strip():
        return "Error: Invalid target path."

    project_root = resolve_project_dir(user_id, project_id).resolve()
    target = (project_root / rel_path).resolve()

    if not str(target).startswith(str(project_root)) or target == project_root:
        return "Error: Cannot delete outside project sandbox."

    if not target.exists():
        return f"Error: '{rel_path}' does not exist."

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return f"✅ Deleted '{rel_path}'."
    except Exception as exc:
        return f"Delete failed: {exc}"


def prepare_download(user_id: str, project_id: str, rel_path: str) -> str:
    """Prepare a file or folder for download.

    - Single file → returns its absolute path directly.
    - Folder → creates a temporary ``.zip`` inside the project sandbox and
      returns the zip path.

    Returns an error string starting with ``"Error:"`` on failure.
    """
    if not user_id or not project_id or not rel_path.strip():
        return "Error: No path specified."

    project_root = resolve_project_dir(user_id, project_id).resolve()
    target = (project_root / rel_path).resolve()

    if not str(target).startswith(str(project_root)):
        return "Error: Path outside project sandbox."
    if not target.exists():
        return f"Error: '{rel_path}' does not exist."

    # Single file — return directly
    if target.is_file():
        return str(target)

    # Folder — create zip
    import tempfile
    import zipfile

    tmp_dir = project_root / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    zip_path = tmp_dir / f"{target.name}.zip"

    try:
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in target.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(target))
        return str(zip_path)
    except Exception as exc:
        return f"Error: ZIP creation failed: {exc}"
