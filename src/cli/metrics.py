#!/usr/bin/env python3
r"""
Habermasian Metrics CLI — compute centrality, cognitive distillation, and
microdemocratic health diagnostics from a Talos RDF/Turtle export.

Usage (from project root)::

    python -m src.cli.metrics --ttl output/ontology_*.ttl
    python -m src.cli.metrics --ttl graph.ttl --top-n 10
    python -m src.cli.metrics --dir output/ --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _entry() -> int:
    """Thin entry-point wrapper that masks internal tracebacks from end-users."""
    try:
        return main()
    except Exception as exc:
        msg = str(exc)
        # Mask absolute paths
        cwd = str(Path.cwd().resolve())
        home = str(Path.home().resolve())
        for prefix in (cwd, home):
            msg = msg.replace(prefix, "<project>")
            msg = msg.replace(prefix + "/", "<project>/")
        print(f"[Error] {msg}", file=sys.stderr)
        return 1


def _sandboxed_path(raw: str) -> Path:
    """Resolve *raw* and enforce it is inside the current working directory.

    Raises
    ------
    SystemExit
        If the resolved path escapes the project directory.
    """
    resolved = Path(raw).resolve()
    cwd = Path.cwd().resolve()
    try:
        resolved.relative_to(cwd)
    except ValueError:
        print(
            f"[Security] Refusing to access path outside project directory: {raw}",
            file=sys.stderr,
        )
        sys.exit(1)
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Habermasian Metrics Engine — Centrality, Distillation & Health"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--ttl", type=str,
        help="Path to a Turtle (.ttl) RDF export from Talos",
    )
    source.add_argument(
        "--dir", type=str,
        help="Directory of Turtle files to batch-analyse",
    )
    parser.add_argument(
        "--top-n", type=int, default=5,
        help="Number of top hub nodes (default: 5)",
    )
    parser.add_argument(
        "--format", type=str, default="json", choices=["json"],
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--no-health", action="store_true",
        help="Skip the health diagnostics report",
    )
    parser.add_argument(
        "--no-distill", action="store_true",
        help="Skip cognitive-tool distillation",
    )
    args = parser.parse_args(argv)

    # ── Resolve and sandbox inputs ──────────────────────────────────────
    if args.ttl:
        ttl_path = _sandboxed_path(args.ttl)
        if not ttl_path.exists():
            print(f"[Error] File not found: {args.ttl}", file=sys.stderr)
            return 1
        ttl_files = [ttl_path]
    else:
        dir_path = _sandboxed_path(args.dir)
        if not dir_path.is_dir():
            print(f"[Error] Directory not found: {args.dir}", file=sys.stderr)
            return 1
        ttl_files = sorted(dir_path.glob("*.ttl"))
        if not ttl_files:
            print(f"[Error] No .ttl files found in {args.dir}", file=sys.stderr)
            return 1

    # ── Lazy imports (after arg validation) ─────────────────────────────
    from src.tools.triples import compute_hub_nodes, distill_cognitive_tools
    from src.analytics.health_diagnostics import graph_health_report

    all_results: list = []

    for ttl_file in ttl_files:
        print(f"[*] Processing: {ttl_file.name} ...", file=sys.stderr)

        ttl_text = ttl_file.read_text(encoding="utf-8")

        result: dict = {"file": str(ttl_file.relative_to(Path.cwd()))}

        # ── Centrality ─────────────────────────────────────────────────
        try:
            import rdflib
            g = rdflib.Graph()
            g.parse(data=ttl_text, format="turtle")

            hubs = compute_hub_nodes(g, top_n=args.top_n)
            result["hub_nodes"] = hubs
            result["hub_count"] = len(hubs)
        except Exception as exc:
            result["hub_nodes_error"] = _mask_path(str(exc))

        # ── Cognitive distillation ──────────────────────────────────────
        if not args.no_distill:
            try:
                import rdflib
                g = rdflib.Graph()
                g.parse(data=ttl_text, format="turtle")

                reframing = distill_cognitive_tools(g)
                result["reframing_paths"] = reframing
                result["reframing_count"] = len(reframing)
            except Exception as exc:
                result["distill_error"] = _mask_path(str(exc))

        # ── Health diagnostics ──────────────────────────────────────────
        if not args.no_health:
            try:
                health = graph_health_report(ttl_text)
                result["health"] = health
            except Exception as exc:
                result["health_error"] = _mask_path(str(exc))

        all_results.append(result)

    print(json.dumps(all_results if len(all_results) > 1 else all_results[0], indent=2))
    return 0


def _mask_path(msg: str) -> str:
    """Strip absolute filesystem paths from an error message."""
    cwd = str(Path.cwd().resolve())
    home = str(Path.home().resolve())
    for prefix in sorted([cwd, home], key=len, reverse=True):
        msg = msg.replace(prefix, "<project>")
        msg = msg.replace(prefix + "/", "<project>/")
    return msg


if __name__ == "__main__":
    sys.exit(_entry())
