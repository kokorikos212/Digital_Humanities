"""
Image transcription ingestion — converts image files and PDF scans to plain text
with optional Greek/English translation via Bytez VLM API.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def transcribe_document_image(
    image_path: str,
    target_language: str = "Original",
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Extract text from a document image or PDF scan.

    Parameters
    ----------
    image_path:
        Path to the image/PDF file.
    target_language:
        ``"Original"`` (default), ``"Translate to English"``, or
        ``"Translate to Greek"``.
    user_id:
        Active user for key resolution (user-saved → env → config).
    api_key:
        Explicit Bytez API key (overrides resolution).

    Returns
    -------
    Extracted text, or a placeholder notice.
    """
    p = Path(image_path)
    if not p.exists():
        return "Error: File does not exist."

    suffix = p.suffix.lower()

    # Plain text / markdown → pass through
    if suffix in (".txt", ".md"):
        try:
            return p.read_text(encoding="utf-8")
        except Exception as exc:
            return f"Error reading text file: {exc}"

    # Build translation prompt
    prompt = "Transcribe all text from this document image accurately."
    if target_language == "Translate to English":
        prompt += " Translate the extracted text into English."
    elif target_language == "Translate to Greek":
        prompt += " Translate the extracted text into Greek."

    # Resolve key: explicit → user-saved → env vars
    from src.auth_keys import resolve_api_key

    bytez_key = (
        api_key
        or (resolve_api_key(user_id, "BYTEZ_API_KEY") if user_id else "")
        or (resolve_api_key(user_id, "LLM_API_KEY") if user_id else "")
        or os.getenv("BYTEZ_API_KEY", "")
        or os.getenv("LLM_API_KEY", "")
    )
    if bytez_key:
        try:
            import requests

            with open(p, "rb") as f:
                response = requests.post(
                    "https://api.bytez.com/v1/model/run",
                    headers={"Authorization": f"Bearer {bytez_key}"},
                    files={"file": f},
                    data={
                        "model": "Qwen/Qwen2-VL-7B-Instruct",
                        "prompt": prompt,
                    },
                    timeout=60,
                )
            if response.status_code == 200:
                data = response.json()
                return data.get("output", data.get("text", str(data)))
        except Exception as exc:
            print(f"[Warning] Bytez OCR API failed: {exc}")

    # PDF → try pdftotext if available
    if suffix == ".pdf":
        try:
            import subprocess
            result = subprocess.run(
                ["pdftotext", "-layout", str(p), "-"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

    return (
        f"[OCR Notice] File '{p.name}' received. "
        "Configure BYTEZ_API_KEY or LLM_API_KEY to enable live text extraction."
    )
