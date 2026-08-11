#!/usr/bin/env python3
"""
Batch corpus divergence analysis — ingests two faction document directories,
computes weighted log-odds z-scores, distribution metrics, and exports reports.

Usage (from project root)::

    python -m src.cli.analyze_factions --dir-a factions/faction_a \\
                                       --dir-b factions/faction_b \\
                                       --out-dir analysis_results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.tools.statistics import compute_corpus_divergence, compute_log_odds_ratio


def load_directory_corpus(dir_path: Path) -> str:
    """Recursively read and concatenate all ``.txt`` and ``.md`` files."""
    if not dir_path.exists() or not dir_path.is_dir():
        return ""

    texts = []
    for ext in ("*.txt", "*.md"):
        for fpath in sorted(dir_path.rglob(ext)):
            try:
                content = fpath.read_text(encoding="utf-8").strip()
                if content:
                    texts.append(content)
            except Exception as exc:
                print(f"[Warning] Failed to read {fpath}: {exc}")

    return "\n\n".join(texts)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Batch Statistical Analysis — Faction Vocabulary Divergence"
    )
    parser.add_argument(
        "--dir-a", type=str, required=True,
        help="Relative path to Faction A documents folder",
    )
    parser.add_argument(
        "--dir-b", type=str, required=True,
        help="Relative path to Faction B documents folder",
    )
    parser.add_argument(
        "--out-dir", type=str, default="analysis_results",
        help="Relative path for output directory",
    )
    parser.add_argument(
        "--top-n", type=int, default=20,
        help="Number of top log-odds terms per faction",
    )
    args = parser.parse_args(argv)

    path_a = Path(args.dir_a).resolve()
    path_b = Path(args.dir_b).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    text_a = load_directory_corpus(path_a)
    text_b = load_directory_corpus(path_b)

    if not text_a or not text_b:
        print("[Error] One or both directory corpora are empty or unreadable.")
        return

    print(f"[*] Processing Faction A ({len(text_a):,} chars) vs Faction B ({len(text_b):,} chars)...")

    # 1. Divergence metrics
    metrics = compute_corpus_divergence(text_a, text_b)

    # 2. Discriminative terms
    log_odds_df = compute_log_odds_ratio(text_a, text_b, top_n=args.top_n)

    # 3. Export summary.json
    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps({
            "metrics": metrics,
            "faction_a_char_count": len(text_a),
            "faction_b_char_count": len(text_b),
            "dir_a": str(args.dir_a),
            "dir_b": str(args.dir_b),
        }, indent=2),
        encoding="utf-8",
    )

    # 4. Export CSV
    csv_path = out_dir / "discriminative_terms.csv"
    log_odds_df.to_csv(csv_path, index=False)

    # 5. Export Markdown report
    report_path = out_dir / "divergence_report.md"
    sig_note = (
        "✅ Statistically Significant (p < 0.05)"
        if metrics["statistically_significant"]
        else "⚠️ Not Statistically Significant"
    )
    report_md = f"""# 📊 Faction Vocabulary Divergence Analysis

## Executive Summary
- **Jensen-Shannon Divergence (JSD):** `{metrics['jsd']}` (Scale 0–1)
- **Chi-Square p-value:** `{metrics['chi2_p_value']}` — {sig_note}
- **Cosine Similarity:** `{metrics['cosine_similarity']}`

## Top Discriminative Vocabulary (Weighted Log-Odds z-Scores)
{log_odds_df.to_string(index=False)}
"""
    report_path.write_text(report_md, encoding="utf-8")

    print(f"[+] Analysis Complete! Outputs saved to: {out_dir}/")
    print(f"    - Summary: {summary_path}")
    print(f"    - Terms CSV: {csv_path}")
    print(f"    - Report: {report_path}")


if __name__ == "__main__":
    main()
