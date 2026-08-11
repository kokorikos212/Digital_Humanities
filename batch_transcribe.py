#!/usr/bin/env python3
"""Batch image transcription — transcribe a directory of images/PDFs."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cli.batch_transcribe import main

if __name__ == "__main__":
    main()
