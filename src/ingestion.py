"""
File ingestion handler — safely saves uploaded documents into a user's project
directory and maintains a lightweight project manifest.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.config import resolve_project_dir

SUPPORTED_EXTENSIONS = {".txt", ".md", ".ttl", ".json", ".pdf", ".csv", ".rdf", ".xml"}


def save_uploaded_files(
    uploaded_files: List[Any], user_id: str, project_id: str
) -> Dict[str, Any]:
    """Copy uploaded files into ``data/users/{uid}/{pid}/documents/``.

    Parameters
    ----------
    uploaded_files:
        List of file-like objects with a ``.name`` attribute (e.g. Gradio
        ``gr.File`` return values, or ``pathlib.Path`` instances).
    user_id:
        User identifier (e.g. ``"alice"``).
    project_id:
        Project identifier (e.g. ``"debate_analysis"``).

    Returns
    -------
    A dict with ``status``, ``saved_files``, ``total_files``, and
    ``project_dir``.
    """
    project_dir = resolve_project_dir(user_id, project_id)
    doc_dir = project_dir / "documents"
    saved_files: List[str] = []

    for file_obj in uploaded_files:
        # Gradio File returns a temp path string; Path objects pass through
        if isinstance(file_obj, (str, Path)):
            source = Path(file_obj)
            fname = source.name
        else:
            # File-like with .name attribute
            fname = Path(file_obj.name).name
            source = Path(file_obj.name)

        if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        target = doc_dir / fname
        shutil.copy(str(source), str(target))
        saved_files.append(fname)

    # Update project manifest
    manifest_path = project_dir / "manifest.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    manifest.setdefault("documents", [])
    for fname in saved_files:
        if fname not in manifest["documents"]:
            manifest["documents"].append(fname)
    manifest["last_updated"] = datetime.now(timezone.utc).isoformat()

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "saved_files": saved_files,
        "total_files": len(saved_files),
        "project_dir": str(project_dir),
    }


def save_transcribed_document(
    user_id: str, project_id: str, filename: str, content: str
) -> str:
    """Persist transcribed OCR text as a ``.md`` file inside the project documents dir.

    Returns a status message.
    """
    if not user_id or not project_id or not content.strip():
        return "Error: Invalid user, project, or empty content."

    proj_dir = resolve_project_dir(user_id, project_id)
    doc_dir = proj_dir / "documents"
    doc_dir.mkdir(parents=True, exist_ok=True)

    clean_name = Path(filename).stem + "_transcript.md"
    target = doc_dir / clean_name
    target.write_text(content, encoding="utf-8")

    return f"Successfully saved transcript to /documents/{clean_name}"
