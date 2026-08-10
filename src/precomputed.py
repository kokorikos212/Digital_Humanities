"""
Pre-computed asset loader for benchmark examples.

Maps benchmark example titles to pre-analyzed graph artifacts on disk,
enabling instant UI population without live DeepSeek API calls.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

_BASE = Path(__file__).resolve().parent.parent / "assets" / "precomputed"

PRECOMPUTED_MAP: Dict[str, str] = {
    "Case 1: University Budget Debate": "case1_budget_debate",
    "Case 2: Modal & Conditional Claims (Dr. Aris)": "case2_modal_claims",
    "Case 3: Reified Events (Dr. Chen Presentation)": "case3_event_reification",
}


def load_precomputed_asset(example_title: str) -> Optional[Dict[str, Any]]:
    """Load pre-computed graph, markdown, JSON, and Turtle artifacts.

    Parameters
    ----------
    example_title:
        A key from ``PRECOMPUTED_MAP``.

    Returns
    -------
    A dict with keys ``ttl``, ``html``, ``md``, ``json``, or ``None``
    if the folder or files are missing.
    """
    folder_name = PRECOMPUTED_MAP.get(example_title)
    if not folder_name:
        return None

    folder = _BASE / folder_name
    if not folder.exists():
        return None

    try:
        ttl_data = (folder / "graph.ttl").read_text(encoding="utf-8")
        html_data = (folder / "graph.html").read_text(encoding="utf-8")
        md_data = (folder / "note.md").read_text(encoding="utf-8")
        json_data = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        return {"ttl": ttl_data, "html": html_data, "md": md_data, "json": json_data}
    except Exception as exc:
        print(f"Error loading pre-computed asset for {example_title}: {exc}")
        return None
