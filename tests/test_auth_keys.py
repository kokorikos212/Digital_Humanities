"""
API key management tests — save, load, resolve, mask.
"""

import json
import os
from pathlib import Path

from src.auth_keys import (
    get_user_settings_path,
    save_user_keys,
    load_user_keys,
    resolve_api_key,
    mask_key,
)


class TestAuthKeys:
    def test_save_creates_settings_file(self):
        save_user_keys("keytest_user", {"DEEPSEEK_KEY": "sk-test-abc"})
        sf = get_user_settings_path("keytest_user")
        assert sf.exists()
        data = json.loads(sf.read_text())
        assert data["api_keys"]["DEEPSEEK_KEY"] == "sk-test-abc"
        sf.unlink()

    def test_load_returns_saved_keys(self):
        save_user_keys("keytest_user", {"BYTEZ_API_KEY": "bytez-123"})
        keys = load_user_keys("keytest_user")
        assert keys.get("BYTEZ_API_KEY") == "bytez-123"
        get_user_settings_path("keytest_user").unlink()

    def test_empty_value_removes_key(self):
        save_user_keys("keytest_user", {"DEEPSEEK_KEY": "sk-abc"})
        save_user_keys("keytest_user", {"DEEPSEEK_KEY": ""})
        keys = load_user_keys("keytest_user")
        assert "DEEPSEEK_KEY" not in keys
        get_user_settings_path("keytest_user").unlink()

    def test_masked_value_not_saved(self):
        save_user_keys("keytest_user", {"DEEPSEEK_KEY": "sk-real"})
        save_user_keys("keytest_user", {"DEEPSEEK_KEY": "••••sk-real"})
        keys = load_user_keys("keytest_user")
        assert keys["DEEPSEEK_KEY"] == "sk-real"  # unchanged
        get_user_settings_path("keytest_user").unlink()

    def test_resolve_user_key_over_env(self):
        save_user_keys("keytest_user", {"DEEPSEEK_KEY": "user-key"})
        result = resolve_api_key("keytest_user", "DEEPSEEK_KEY")
        assert result == "user-key"
        get_user_settings_path("keytest_user").unlink()

    def test_resolve_falls_back_to_env(self):
        os.environ["TEST_KEY_XYZ"] = "env-value"
        result = resolve_api_key("no_such_user_99", "TEST_KEY_XYZ")
        assert result == "env-value"
        del os.environ["TEST_KEY_XYZ"]

    def test_mask_key_short(self):
        assert mask_key("abc") == "••••••••"

    def test_mask_key_long(self):
        m = mask_key("sk-1234567890abcdef")
        assert m.startswith("sk-1")
        assert m.endswith("cdef")
        assert "••••" in m
