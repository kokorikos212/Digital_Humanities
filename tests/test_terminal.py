"""
Sandboxed terminal tests — path confinement, blocked commands, timeouts.
"""

import shutil

from src.config import resolve_project_dir, config
from src.tools.terminal import execute_project_bash


class TestTerminal:
    """Verify execute_project_bash sandboxing."""

    def test_pwd_returns_inside_project(self):
        """pwd should show a path inside the project directory."""
        out, cwd = execute_project_bash("term_user", "term_proj", "pwd")
        assert "data/users/term_user/projects/term_proj" in out
        shutil.rmtree(config.project_root / "data" / "users" / "term_user", ignore_errors=True)

    def test_ls_lists_documents(self):
        """ls should show the documents folder."""
        resolve_project_dir("term_user", "term_proj")  # ensures folders exist
        out, _ = execute_project_bash("term_user", "term_proj", "ls")
        assert "documents" in out.lower()
        shutil.rmtree(config.project_root / "data" / "users" / "term_user", ignore_errors=True)

    def test_cd_navigate_and_back(self):
        """cd into documents then cd .. back to root."""
        out1, cwd1 = execute_project_bash("term_user", "term_proj", "cd documents")
        assert "documents" in cwd1

        out2, cwd2 = execute_project_bash("term_user", "term_proj", "cd ..", cwd1)
        assert cwd2 in ("", ".")
        shutil.rmtree(config.project_root / "data" / "users" / "term_user", ignore_errors=True)

    def test_cd_escape_blocked(self):
        """cd ../../../ should be blocked."""
        out, cwd = execute_project_bash("term_user", "term_proj", "cd ../../../")
        assert "cannot navigate outside" in out.lower()
        shutil.rmtree(config.project_root / "data" / "users" / "term_user", ignore_errors=True)

    def test_sudo_blocked(self):
        """sudo should return security error."""
        out, _ = execute_project_bash("term_user", "term_proj", "sudo ls")
        assert "restricted" in out.lower()

    def test_sleep_timeout(self):
        """sleep 15 should be killed by the 10s timeout."""
        out, _ = execute_project_bash("term_user", "term_proj", "sleep 15")
        assert "timed out" in out.lower()

    def test_empty_user_returns_error(self):
        """Empty user/project returns an error message in output or cwd."""
        out, cwd = execute_project_bash("", "", "pwd")
        assert "error" in (out + cwd).lower()
