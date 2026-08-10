"""
Pre-computed asset loader tests.
"""

import json
import tempfile
from pathlib import Path

from src.precomputed import PRECOMPUTED_MAP, load_precomputed_asset


def _write_asset(folder: Path):
    """Write minimal valid pre-computed asset files to *folder*."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "graph.ttl").write_text('@prefix ex: <http://example.org/> .\nex:A a ex:Thing .', encoding="utf-8")
    (folder / "graph.html").write_text("<html><body>Graph</body></html>", encoding="utf-8")
    (folder / "note.md").write_text("# Test Note", encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")


class TestPrecomputedLoader:
    """Verify load_precomputed_asset behaviour."""

    def test_unknown_key_returns_none(self):
        assert load_precomputed_asset("nonexistent key") is None

    def test_missing_folder_returns_none(self):
        """Key exists in map but folder is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            import src.precomputed as pc
            original_base = pc._BASE
            pc._BASE = Path(tmp)
            try:
                result = load_precomputed_asset(list(PRECOMPUTED_MAP.keys())[0])
                assert result is None
            finally:
                pc._BASE = original_base

    def test_loads_all_fields(self):
        """All four file types are correctly loaded."""
        with tempfile.TemporaryDirectory() as tmp:
            import src.precomputed as pc
            original_base = pc._BASE
            pc._BASE = Path(tmp)
            try:
                key = list(PRECOMPUTED_MAP.keys())[0]
                folder = Path(tmp) / PRECOMPUTED_MAP[key]
                _write_asset(folder)

                result = load_precomputed_asset(key)
                assert result is not None
                assert result["ttl"].startswith("@prefix")
                assert "<html" in result["html"].lower()
                assert result["md"] == "# Test Note"
                assert result["json"] == {"status": "ok"}
            finally:
                pc._BASE = original_base

    def test_ttl_parses_with_rdflib(self):
        """Loaded Turtle must be valid RDF."""
        import rdflib
        with tempfile.TemporaryDirectory() as tmp:
            import src.precomputed as pc
            original_base = pc._BASE
            pc._BASE = Path(tmp)
            try:
                key = list(PRECOMPUTED_MAP.keys())[0]
                folder = Path(tmp) / PRECOMPUTED_MAP[key]
                _write_asset(folder)

                result = load_precomputed_asset(key)
                g = rdflib.Graph()
                g.parse(data=result["ttl"], format="turtle")
                assert len(g) == 1
            finally:
                pc._BASE = original_base

    def test_empty_folder_raises_no_crash(self):
        """Partially populated folder returns None gracefully."""
        with tempfile.TemporaryDirectory() as tmp:
            import src.precomputed as pc
            original_base = pc._BASE
            pc._BASE = Path(tmp)
            try:
                key = list(PRECOMPUTED_MAP.keys())[0]
                folder = Path(tmp) / PRECOMPUTED_MAP[key]
                folder.mkdir(parents=True, exist_ok=True)
                (folder / "graph.ttl").write_text("@prefix ex: <http://example.org/> .", encoding="utf-8")
                # Missing graph.html, note.md, summary.json

                result = load_precomputed_asset(key)
                assert result is None
            finally:
                pc._BASE = original_base
