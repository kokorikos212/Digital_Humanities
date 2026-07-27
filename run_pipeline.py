#!/usr/bin/env python3
"""
Entry point for the ontological conversation analysis pipeline.

Usage:
    python run_pipeline.py                          # run the default example
    python run_pipeline.py --text "Your text here"  # analyze custom text
    python run_pipeline.py --file conversation.txt  # analyze a text file
    python run_pipeline.py --prompt ex_conversation_ontology  # named prompt
    python run_pipeline.py --text "..." --max-iter 20 --model deepseek-chat
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cli import main

if __name__ == "__main__":
    main()
