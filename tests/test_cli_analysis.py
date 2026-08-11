"""
CLI batch analysis integration tests — verify directory-based faction analysis.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class TestCLIAnalyzeFactions:
    """Verify the batch CLI produces expected outputs."""

    def test_batch_run_produces_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dir_a = root / "faction_a"
            dir_b = root / "faction_b"
            out = root / "results"
            dir_a.mkdir(parents=True)
            dir_b.mkdir(parents=True)
            (dir_a / "speech1.txt").write_text(
                "lab equipment research computing academic output rankings priority budget allocation"
            )
            (dir_a / "proposal.md").write_text(
                "modernizing computing labs academic standards research excellence"
            )
            (dir_b / "motion.txt").write_text(
                "housing subsidies student insecurity rent burden affordability crisis"
            )
            (dir_b / "statement.md").write_text(
                "forty percent of students face severe housing insecurity"
            )

            result = subprocess.run(
                [sys.executable, "-m", "src.cli.analyze_factions",
                 "--dir-a", str(dir_a), "--dir-b", str(dir_b),
                 "--out-dir", str(out), "--top-n", "10"],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"CLI failed: {result.stderr}"

            assert (out / "summary.json").exists()
            assert (out / "discriminative_terms.csv").exists()
            assert (out / "divergence_report.md").exists()

    def test_summary_json_contains_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            da, db = root / "a", root / "b"
            out = root / "out"
            da.mkdir(parents=True); db.mkdir(parents=True)
            (da / "a.txt").write_text("lab equipment research computing academic")
            (db / "b.txt").write_text("housing subsidies student rent burden")

            subprocess.run(
                [sys.executable, "-m", "src.cli.analyze_factions",
                 "--dir-a", str(da), "--dir-b", str(db), "--out-dir", str(out)],
                capture_output=True,
            )

            summary = json.loads((out / "summary.json").read_text())
            assert "metrics" in summary
            assert summary["metrics"]["jsd"] >= 0

    def test_csv_has_expected_columns(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            da, db = root / "a", root / "b"
            out = root / "out"
            da.mkdir(parents=True); db.mkdir(parents=True)
            (da / "a.txt").write_text("research computing lab equipment")
            (db / "b.txt").write_text("housing rent student crisis")

            subprocess.run(
                [sys.executable, "-m", "src.cli.analyze_factions",
                 "--dir-a", str(da), "--dir-b", str(db), "--out-dir", str(out)],
                capture_output=True,
            )
            df = pd.read_csv(out / "discriminative_terms.csv")
            assert "word" in df.columns
            assert "z_score" in df.columns

    def test_empty_dir_errors_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            da, db = root / "a", root / "b"
            out = root / "out"
            da.mkdir(parents=True); db.mkdir(parents=True)
            # Both dirs empty

            result = subprocess.run(
                [sys.executable, "-m", "src.cli.analyze_factions",
                 "--dir-a", str(da), "--dir-b", str(db), "--out-dir", str(out)],
                capture_output=True, text=True,
            )
            assert "empty" in result.stdout.lower() or result.returncode == 0
