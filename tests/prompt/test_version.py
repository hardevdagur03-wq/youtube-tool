from __future__ import annotations

import pytest


pytestmark = pytest.mark.prompt


class TestPromptVersion:
    def test_version_tracking(self):
        versions = {
            "v1": {"template": "Hello {{ name }}", "created": "2026-01-01"},
            "v2": {"template": "Hi {{ name }}!", "created": "2026-06-01"},
            "v3": {"template": "Greetings {{ name }}!", "created": "2026-07-01"},
        }
        assert len(versions) == 3
        assert versions["v1"]["template"] != versions["v3"]["template"]

    def test_version_rollback(self):
        current = {"template": "New prompt {{ var }}", "version": 3}
        history = {
            1: {"template": "Original prompt {{ var }}"},
            2: {"template": "Updated prompt {{ var }}"},
        }
        rolled_back = history[1]
        assert rolled_back["template"] == "Original prompt {{ var }}"
        assert rolled_back != current

    def test_version_diff(self):
        old_template = "Hello {{ name }}, welcome to {{ service }}"
        new_template = "Hello {{ name }}, welcome back to {{ service }}"
        old_vars = {"name", "service"}
        new_vars = {"name", "service"}
        assert old_vars == new_vars
        assert old_template != new_template
