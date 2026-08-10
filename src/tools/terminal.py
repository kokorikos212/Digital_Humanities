"""
Sandboxed bash terminal — executes commands scoped to a user's project directory.

All commands run via ``subprocess.run`` with a 10-second timeout and path
confinement to ``data/users/{uid}/projects/{pid}/``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Tuple

from src.config import resolve_project_dir

BLOCKED_COMMANDS = {"sudo", "su", "shutdown", "reboot", "mkfs", "passwd"}


def execute_project_bash(
    user_id: str,
    project_id: str,
    command: str,
    current_rel_path: str = "",
) -> Tuple[str, str]:
    """Execute a bash command scoped inside the user's project sandbox.

    Parameters
    ----------
    user_id / project_id:
        Identify the sandbox root.
    command:
        Raw shell command string.
    current_rel_path:
        Current working directory relative to the project root (``""`` = root).

    Returns
    -------
    (output_text, new_relative_cwd) — *output_text* may be empty on
    internal commands like ``cd``.  *new_relative_cwd* is the updated
    working directory after ``cd``, otherwise unchanged.
    """
    if not user_id or not project_id:
        return "", "Error: No active user or project selected."

    project_root = resolve_project_dir(user_id, project_id).resolve()
    target_cwd = (project_root / current_rel_path).resolve()

    # Sandbox guardrail — ensure we stay inside the project
    if not str(target_cwd).startswith(str(project_root)) or not target_cwd.exists():
        target_cwd = project_root

    cmd_parts = command.strip().split()
    if not cmd_parts:
        return "", str(target_cwd.relative_to(project_root))

    # Block dangerous commands
    if cmd_parts[0] in BLOCKED_COMMANDS:
        return (
            f"Security Error: Command '{cmd_parts[0]}' is restricted.",
            str(target_cwd.relative_to(project_root)),
        )

    # Handle cd internally (subprocess can't change the parent's cwd)
    if cmd_parts[0] == "cd":
        dest = cmd_parts[1] if len(cmd_parts) > 1 else ""
        new_target = (target_cwd / dest).resolve() if dest else project_root
        if str(new_target).startswith(str(project_root)) and new_target.is_dir():
            new_rel = str(new_target.relative_to(project_root))
            return f"Changed directory to: /{new_rel}", new_rel
        return (
            "Error: Cannot navigate outside project sandbox root.",
            str(target_cwd.relative_to(project_root)),
        )

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(target_cwd),
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        return output.strip() or "(no output)", str(target_cwd.relative_to(project_root))
    except subprocess.TimeoutExpired:
        return "Execution Error: Command timed out (10s limit).", str(
            target_cwd.relative_to(project_root)
        )
    except Exception as exc:
        return f"Execution Error: {exc}", str(target_cwd.relative_to(project_root))
