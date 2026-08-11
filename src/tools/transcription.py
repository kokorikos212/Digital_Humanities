"""
Image transcription ingestion — converts image files and PDF scans to plain text.

Supports API-based VLM/OCR via Bytez or local text fallback.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def transcribe_document_image(
    image_path: Path,
    api_key: Optional[str] = None,
) -> str:
    """Extract text from a document image or PDF scan.

    If *image_path* is already ``.txt`` or ``.md``, its content is returned
    directly.  Otherwise a VLM/OCR API is attempted (BYTEZ_API_KEY env var),
    falling back to a notice that the file was received.

    Parameters
    ----------
    image_path:
        Path to the image/PDF file.
    api_key:
        Bytez API key (defaults to ``BYTEZ_API_KEY`` env var).

    Returns
    -------
    Extracted text, or a placeholder notice.
    """
    if not image_path.exists():
        return "Error: File does not exist."

    suffix = image_path.suffix.lower()

    # Plain text / markdown → pass through
    if suffix in (".txt", ".md"):
        try:
            return image_path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"Error reading text file: {exc}"

    # Bytez VLM / OCR API
    bytez_key = api_key or os.getenv("BYTEZ_API_KEY", "")
    if bytez_key:
        try:
            import requests

            with open(image_path, "rb") as f:
                response = requests.post(
                    "https://api.bytez.com/v1/model/run",
                    headers={"Authorization": f"Bearer {bytez_key}"},
                    files={"file": f},
                    data={"model": "Qwen/Qwen2-VL-7B-Instruct"},
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
                ["pdftotext", "-layout", str(image_path), "-"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

    return (
        f"[Notice] Image uploaded ({image_path.name}). "
        "Configure BYTEZ_API_KEY for automatic VLM transcription."
    )
