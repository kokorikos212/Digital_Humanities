"""
Authentication tests — registration, login, project CRUD.
"""

import json
import shutil
import tempfile
from pathlib import Path

from src.auth import (
    USERS_DIR,
    register_user,
    authenticate_user,
    list_user_projects,
    create_project,
)
from src.config import config


class TestAuth:
    """Verify user registration and login flows."""

    def test_register_creates_credentials(self):
        """Registration creates .credentials.json with hashed password."""
        ok, msg = register_user("testuser_auth", "secret123")
        assert ok
        creds_file = USERS_DIR / "testuser_auth" / ".credentials.json"
        assert creds_file.exists()
        creds = json.loads(creds_file.read_text(encoding="utf-8"))
        assert creds["username"] == "testuser_auth"
        assert "password" in creds
        # Cleanup
        shutil.rmtree(USERS_DIR / "testuser_auth", ignore_errors=True)

    def test_duplicate_username_rejected(self):
        """Same username twice should fail."""
        register_user("dup_user", "pw1")
        ok, msg = register_user("dup_user", "pw2")
        assert not ok
        assert "already exists" in msg.lower()
        shutil.rmtree(USERS_DIR / "dup_user", ignore_errors=True)

    def test_empty_credentials_rejected(self):
        """Empty username or password returns failure."""
        ok, _ = register_user("", "")
        assert not ok
        ok, _ = register_user("user", "")
        assert not ok

    def test_login_correct_password(self):
        """Valid password authenticates successfully."""
        register_user("login_test", "mypassword")
        ok, msg = authenticate_user("login_test", "mypassword")
        assert ok
        assert "successful" in msg.lower()
        shutil.rmtree(USERS_DIR / "login_test", ignore_errors=True)

    def test_login_wrong_password(self):
        """Invalid password is rejected."""
        register_user("wrong_pw", "correct")
        ok, msg = authenticate_user("wrong_pw", "incorrect")
        assert not ok
        assert "invalid" in msg.lower()
        shutil.rmtree(USERS_DIR / "wrong_pw", ignore_errors=True)

    def test_login_nonexistent_user(self):
        """Non-existent user returns failure."""
        ok, msg = authenticate_user("no_such_user_xyz", "any")
        assert not ok
        assert "does not exist" in msg.lower()

    def test_list_projects_empty(self):
        """New user has no projects."""
        register_user("no_projects", "pw")
        projects = list_user_projects("no_projects")
        assert projects == []
        shutil.rmtree(USERS_DIR / "no_projects", ignore_errors=True)

    def test_create_and_list_projects(self):
        """Creating projects reflects in the list."""
        register_user("proj_owner", "pw")
        ok, slug = create_project("proj_owner", "My Debate")
        assert ok
        assert slug == "my_debate"
        projects = list_user_projects("proj_owner")
        assert "my_debate" in projects
        shutil.rmtree(USERS_DIR / "proj_owner", ignore_errors=True)
