"""
CLI entry point for the ontological analysis pipeline.

Extracted from ``run_pipeline.py`` so the UI can import pipeline logic
without triggering argparse.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import time
from pathlib import Path
from typing import Optional

from src.config import config
from src.pipeline import run_pipeline
from src.prompts import NAMED_PROMPTS, SYSTEM_PROMPT, build_analysis_prompt


def load_named_prompt(name: str) -> str | None:
    """Load a prompt by key from the named prompts dict."""
    return NAMED_PROMPTS.get(name)


def list_prompts() -> list[str]:
    """Return available named prompt keys."""
    return list(NAMED_PROMPTS.keys())


def read_text_file(filepath: str) -> str:
    """Read text from a file."""
    return Path(filepath).read_text(encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> None:
    """Parse arguments and run the pipeline.

    Parameters
    ----------
    argv:
        Argument list (defaults to ``sys.argv[1:]``).
    """
    parser = argparse.ArgumentParser(
        description="Ontological Conversation Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python run_pipeline.py
          python run_pipeline.py --text "Dr. Chen presented at Stanford."
          python run_pipeline.py --text "Alice: Hello!\\nBob: Hi Alice!"
          python run_pipeline.py --file my_conversation.txt
          python run_pipeline.py --prompt ex_conversation_ontology
          python run_pipeline.py --list-prompts
        """),
    )

    # Input source
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", "-t", type=str, help="Raw text to analyze")
    group.add_argument("--file", "-f", type=str, help="Path to a text file to analyze")
    group.add_argument(
        "--prompt", "-p", type=str, help="Name of a named prompt"
    )
    group.add_argument(
        "--list-prompts", "-l", action="store_true",
        help="List available named prompts and exit",
    )

    # Pipeline options
    parser.add_argument(
        "--max-iter", "-m", type=int, default=config.max_iterations,
        help=f"Maximum tool-calling iterations (default: {config.max_iterations})",
    )
    parser.add_argument(
        "--model", type=str, default=config.model,
        help=f"LLM model name (default: {config.model})",
    )
    parser.add_argument(
        "--system-prompt", type=str, default=None,
        help="Override the default system prompt (or path to a .txt file)",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Save the final LLM response to this file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print the full LLM response to stdout",
    )

    args = parser.parse_args(argv)

    # ── List prompts mode ────────────────────────────────────────────
    if args.list_prompts:
        print("Available prompts:")
        for key in list_prompts():
            print(f"  - {key}")
        return

    # ── Load env ──────────────────────────────────────────────────────
    try:
        config.load_env()
    except RuntimeError as exc:
        print(f"✗ Config error: {exc}")
        sys.exit(1)

    # ── Resolve input text ───────────────────────────────────────────
    if args.text:
        user_prompt = build_analysis_prompt(args.text)
        source_label = "inline text"
    elif args.file:
        raw = read_text_file(args.file)
        user_prompt = build_analysis_prompt(raw)
        source_label = f"file: {args.file}"
    elif args.prompt:
        user_prompt = load_named_prompt(args.prompt)
        if user_prompt is None:
            print(f"Error: prompt '{args.prompt}' not found.")
            print("Available prompts:")
            for key in list_prompts():
                print(f"  - {key}")
            sys.exit(1)
        source_label = f"prompt: {args.prompt}"
    else:
        user_prompt = load_named_prompt("ex_ontology_basic")
        if user_prompt is None:
            user_prompt = build_analysis_prompt(
                "Dr. Chen presented the research findings at Stanford University."
            )
        source_label = "default (ex_ontology_basic)"

    # ── Resolve system prompt ────────────────────────────────────────
    if args.system_prompt:
        sp_path = Path(args.system_prompt)
        if sp_path.suffix in (".txt", ".md") and sp_path.exists():
            system_prompt = sp_path.read_text().strip()
        else:
            system_prompt = args.system_prompt
    else:
        system_prompt = SYSTEM_PROMPT

    # ── Header ───────────────────────────────────────────────────────
    print("═" * 62)
    print("  Ontological Conversation Analysis Pipeline")
    print("═" * 62)
    print(f"  Source:      {source_label}")
    print(f"  Model:       {args.model}")
    print(f"  Max iters:   {args.max_iter}")
    print("─" * 62)

    # ── Run ──────────────────────────────────────────────────────────
    started = time.monotonic()

    try:
        result = run_pipeline(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            max_iterations=args.max_iter,
            model=args.model,
        )
    except KeyboardInterrupt:
        print("\n⏹  Pipeline interrupted.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n✗ Pipeline failed: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.monotonic() - started

    # ── Output ───────────────────────────────────────────────────────
    print("─" * 62)
    print(f"  Completed in {elapsed:.1f}s")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        print(f"  Response saved → {out_path}")
    else:
        config.ensure_output_dirs()
        ts = int(time.time())
        out_path = config.output_dir / f"response_{ts}.json"
        out_path.write_text(result, encoding="utf-8")
        print(f"  Response saved → {out_path}")

    if args.verbose:
        print("═" * 62)
        print(result)
        print("═" * 62)
    else:
        preview = result[:500]
        if len(result) > 500:
            preview += "\n… (truncated — use --verbose for full output)"
        print(f"  Preview:\n{preview}")

    print()
    print("  Output files generated by tools during the run:")
    for sub in ["graphs", "rdf", "conversations", "verse"]:
        subdir = config.output_dir / sub
        if subdir.exists():
            files = sorted(subdir.iterdir())
            for f in files:
                if f.is_file():
                    size_kb = f.stat().st_size / 1024
                    try:
                        rel = f.relative_to(config.project_root)
                    except ValueError:
                        rel = f
                    print(f"    {rel} ({size_kb:.1f} KB)")
    print("═" * 62)
