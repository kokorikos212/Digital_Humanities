"""
Lightweight debug tracer — logs every UI handler call with timestamp and args.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable


def trace(prefix: str = "") -> Callable:
    """Decorator that prints ``[HH:MM:SS] prefix(args...) → result_preview`` on every call.

    Usage::

        @trace("OCR")
        def handle_ocr(file_obj, lang, uid):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            ts = time.strftime("%H:%M:%S")
            tag = f"[{ts}]" + (f" {prefix}" if prefix else "")
            # Summarize args — truncate long strings
            short = []
            for a in args:
                if isinstance(a, str) and len(a) > 80:
                    short.append(f"{a[:40]}...{a[-20:]}")
                elif a is None:
                    short.append("None")
                elif isinstance(a, bool):
                    short.append(str(a))
                else:
                    s = str(a)
                    short.append(s[:60] + ("..." if len(s) > 60 else ""))
            sig = ", ".join(short)
            print(f"{tag} → {fn.__name__}({sig})", flush=True)
            try:
                result = fn(*args, **kwargs)
                preview = _preview(result)
                print(f"{tag} ← {fn.__name__} → {preview}", flush=True)
                return result
            except Exception as exc:
                print(f"{tag} ✗ {fn.__name__} ERROR: {exc}", flush=True)
                raise
        return wrapper
    return decorator


def log(action: str, detail: str = "") -> None:
    """Print a one-shot debug message."""
    ts = time.strftime("%H:%M:%S")
    msg = f"[{ts}] {action}"
    if detail:
        msg += f" — {detail}"
    print(msg, flush=True)


def _preview(result: Any) -> str:
    """Return a short preview string for a result value."""
    if result is None:
        return "None"
    if isinstance(result, str):
        if len(result) > 80:
            return f"str({len(result)}c) '{result[:50]}...'"
        return f"'{result}'"
    if isinstance(result, (list, tuple)):
        return f"{type(result).__name__}({len(result)} items)"
    if isinstance(result, dict):
        return f"dict(keys={list(result.keys())[:5]})"
    return type(result).__name__
