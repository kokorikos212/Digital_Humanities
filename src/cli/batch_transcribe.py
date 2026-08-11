#!/usr/bin/env python3
"""
Batch image transcription — transcribe a directory of images/PDFs and save
transcripts to the project documents folder.

Usage (from project root)::

    python -m src.cli.batch_transcribe --dir scans/ \\
                                       --user alice --project debate_analysis \\
                                       --lang "Translate to English"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.auth_keys import resolve_api_key
from src.ingestion import save_transcribed_document
from src.tools.transcription import transcribe_document_image


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Batch image/PDF transcription → project documents"
    )
    parser.add_argument(
        "--dir", type=str, required=True,
        help="Directory containing images/PDFs to transcribe",
    )
    parser.add_argument(
        "--user", type=str, required=True,
        help="User ID for project sandbox",
    )
    parser.add_argument(
        "--project", type=str, required=True,
        help="Project ID for project sandbox",
    )
    parser.add_argument(
        "--lang", type=str, default="Original",
        choices=["Original", "Translate to English", "Translate to Greek"],
        help="Target language for transcription",
    )
    args = parser.parse_args(argv)

    source = Path(args.dir)
    if not source.exists() or not source.is_dir():
        print(f"[Error] Directory not found: {args.dir}")
        return

    bytez_key = resolve_api_key(args.user, "BYTEZ_API_KEY")

    exts = {".png", ".jpg", ".jpeg", ".pdf", ".bmp"}
    files = sorted(f for f in source.iterdir() if f.suffix.lower() in exts)
    if not files:
        print(f"[Error] No image/PDF files found in {args.dir}")
        return

    print(f"[*] Transcribing {len(files)} file(s) for user={args.user} project={args.project}...")
    ok, fail = 0, 0

    for f in files:
        print(f"  -> {f.name} ... ", end="", flush=True)
        text = transcribe_document_image(str(f), target_language=args.lang, api_key=bytez_key)
        if text.startswith("Error") or text.startswith("[OCR Notice]"):
            print("SKIPPED (no API key or read error)")
            fail += 1
            continue
        result = save_transcribed_document(args.user, args.project, f.name, text)
        if "Successfully saved" in result:
            print("OK")
            ok += 1
        else:
            print(f"FAILED: {result}")
            fail += 1

    print(f"\n[+] Done. {ok} transcribed, {fail} skipped/failed.")


if __name__ == "__main__":
    main()
