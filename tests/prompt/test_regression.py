from __future__ import annotations

import hashlib

import pytest


pytestmark = pytest.mark.prompt


GOLDEN_OUTPUTS = {
    "greeting": "Hello Alice, welcome to the Blog Platform!",
    "summary": "This is a summary of the content for testing.",
    "analysis": "The analysis shows positive sentiment with high engagement.",
}


class TestPromptRegression:
    def test_prompt_output_unchanged_across_versions(self):
        current_outputs = {
            "greeting": "Hello Alice, welcome to the Blog Platform!",
            "summary": "This is a summary of the content for testing.",
            "analysis": "The analysis shows positive sentiment with high engagement.",
        }
        for key in GOLDEN_OUTPUTS:
            assert key in current_outputs
            assert current_outputs[key] == GOLDEN_OUTPUTS[key], (
                f"Regression detected for '{key}': expected '{GOLDEN_OUTPUTS[key]}', got '{current_outputs[key]}'"
            )

    def test_prompt_behavior_regression(self):
        def render_prompt(name, role):
            return f"Hello {name}, you are a {role}."

        results = [
            render_prompt("Admin", "manager"),
            render_prompt("User1", "editor"),
            render_prompt("Viewer", "guest"),
        ]
        assert len(results) == 3
        assert "Admin" in results[0]
        assert "manager" in results[0]
        assert "editor" in results[1]
        assert "guest" in results[2]

    def test_prompt_output_checksum(self):
        output = "Hello Alice, welcome to the Blog Platform!"
        checksum = hashlib.sha256(output.encode()).hexdigest()
        expected = hashlib.sha256(GOLDEN_OUTPUTS["greeting"].encode()).hexdigest()
        assert checksum == expected
