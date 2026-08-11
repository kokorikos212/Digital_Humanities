"""
Image transcription ingestion — converts image files and PDF scans to plain text
with optional Greek/English translation via Hugging Face Inference API.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional


def transcribe_document_image(
    image_path: str,
    target_language: str = "Original",
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Extract text from a document image or PDF scan via HF VLM.

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
        Explicit HF token (overrides resolution).

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

    # Build prompt
    prompt = (
        "Transcribe all text from this document image accurately. "
        "Return ONLY the raw transcribed text. Do NOT add any introduction, "
        "commentary, headers, footers, markdown formatting, or any text "
        "that is not present in the original document."
    )
    if target_language == "Translate to English":
        prompt += " Translate the extracted text into English."
    elif target_language == "Translate to Greek":
        prompt += " Translate the extracted text into Greek."

    # Resolve HF token
    from src.auth_keys import resolve_api_key
    from src.config import config as _cfg

    token = (
        api_key
        or (resolve_api_key(user_id, "HF_TOKEN") if user_id else "")
        or _cfg.hf_token
    )
    if not token:
        token = _cfg.llm_api_key  # fallback: try LLM key

    if token:
        try:
            import time as _time
            from huggingface_hub import InferenceClient

            with open(p, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            ext = suffix.lstrip(".").replace("jpeg", "jpg")
            data_uri = f"data:image/{ext};base64,{img_b64}"

            client = InferenceClient(api_key=token)

            # Retry with exponential backoff for HF rate limits (429)
            max_retries, delay = 3, 2.0
            for attempt in range(max_retries):
                try:
                    completion = client.chat.completions.create(
                        model=_cfg.vl_model,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": data_uri}},
                            ],
                        }],
                        max_tokens=2000,
                    )
                    return completion.choices[0].message.content or ""
                except Exception as exc:
                    msg = str(exc)
                    if "429" in msg and attempt < max_retries - 1:
                        print(f"[Info] HF rate limited (429), retrying in {delay}s...")
                        _time.sleep(delay)
                        delay *= 2
                    else:
                        raise
        except Exception as exc:
            print(f"[Warning] HF VLM API failed: {exc}")

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
        "Configure HF_TOKEN to enable VLM transcription."
    )
