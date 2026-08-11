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

    from src.config import config as _cfg

    bytez_key = (
        api_key
        or (resolve_api_key(user_id, "BYTEZ_API_KEY") if user_id else "")
        or (resolve_api_key(user_id, "LLM_API_KEY") if user_id else "")
        or _cfg.bytez_key
        or _cfg.llm_api_key
    )
    if bytez_key:
        try:
            import base64
            import requests

            # Read and encode image as base64 data URI
            with open(p, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = suffix.lstrip(".")
            data_uri = f"data:image/{ext};base64,{img_b64}"

            payload = {
                "model": _cfg.bytez_vl_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                "max_tokens": 2000,
            }
            response = requests.post(
                _cfg.bytez_api_url,
                headers={
                    "Authorization": f"Bearer {bytez_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            if response.status_code == 200:
                data = response.json()
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", str(data))
                )
            else:
                print(f"[Warning] Bytez API returned {response.status_code}: {response.text[:300]}")
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
