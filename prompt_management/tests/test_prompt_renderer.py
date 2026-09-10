from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from prompt_management.prompt_cache import PromptCache
from prompt_management.prompt_loader import PromptLoader
from prompt_management.prompt_renderer import PromptRenderer


@pytest.fixture
def renderer():
    with tempfile.TemporaryDirectory() as tmp:
        prompts_dir = Path(tmp) / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        (prompts_dir / "shared").mkdir(parents=True, exist_ok=True)
        (prompts_dir / "partials").mkdir(parents=True, exist_ok=True)
        (prompts_dir / "templates").mkdir(parents=True, exist_ok=True)

        (prompts_dir / "test_prompt.md").write_text(
            "---\nprompt_id: p_test\nname: Test\ndescription: A test prompt\n---\n\nHello {{name}}!",
            encoding="utf-8",
        )

        style_partial = """
## Writing Style Guidelines
Use {{tone}} tone.
"""
        (prompts_dir / "shared" / "writing_style.md").write_text(style_partial, encoding="utf-8")

        (prompts_dir / "analysis.md").write_text(
            "---\nprompt_id: p_analysis_v1\nname: Content Analysis\nversion: 1.0.0\nstatus: production\ncategory: analysis\ntags: [content, analysis]\n---\n\nAnalyze this: {{transcript}}\nTitle: {{title}}",
            encoding="utf-8",
        )

        loader = PromptLoader(prompts_dir)
        cache = PromptCache(default_ttl=60.0)
        yield PromptRenderer(loader, cache)


class TestPromptRenderer:
    def test_render_simple_variable(self, renderer):
        result = renderer.render_content("Hello {{name}}!", {"name": "World"})
        assert result == "Hello World!"

    def test_render_multiple_variables(self, renderer):
        result = renderer.render_content(
            "{{greeting}} {{name}}, your score is {{score}}",
            {"greeting": "Hi", "name": "Alice", "score": 95},
        )
        assert result == "Hi Alice, your score is 95"

    def test_render_missing_variable_keeps_placeholder(self, renderer):
        result = renderer.render_content("Hello {{name}}!", {})
        assert "{{name}}" in result

    def test_render_dict_variable(self, renderer):
        result = renderer.render_content("{{user}}", {"user": {"name": "Bob", "age": 30}})
        assert '"name": "Bob"' in result

    def test_render_conditional_true(self, renderer):
        result = renderer.render_content("{{#if show}}visible{{/if}}", {"show": True})
        assert result == "visible"

    def test_render_conditional_false(self, renderer):
        result = renderer.render_content("{{#if show}}visible{{/if}}", {"show": False})
        assert result == ""

    def test_render_loop(self, renderer):
        result = renderer.render_content(
            "{{#each items}}{{name}}{{/each}}",
            {"items": [{"name": "A"}, {"name": "B"}]},
        )
        assert result == "A\nB"

    def test_render_empty_loop(self, renderer):
        result = renderer.render_content("{{#each items}}{{name}}{{/each}}", {"items": []})
        assert result == ""

    def test_resolve_partials(self, renderer):
        result = renderer.resolve_partials("{{>writing_style}}", {"tone": "professional"})
        assert result != ""
        assert "professional" in result

    def test_missing_partial(self, renderer):
        result = renderer.resolve_partials("{{>nonexistent_partial_xyz}}", {})
        assert "missing partial" in result

    def test_get_unresolved_variables(self, renderer):
        vars = renderer.get_unresolved_variables("{{a}} {{b}} {{c}}")
        assert sorted(vars) == ["a", "b", "c"]

    def test_get_partial_refs(self, renderer):
        refs = renderer.get_partial_refs("{{>header}} {{>footer}}")
        assert refs == ["header", "footer"]

    def test_compile_template(self, renderer):
        compiled = renderer.compile_template("test_prompt")
        assert compiled is not None
        assert "{{name}}" in compiled

    def test_cache_invalidation(self, renderer):
        renderer.render_content("{{x}}", {"x": "1"})
        renderer.invalidate_cache()
        assert len(renderer._compiled_cache) == 0

    def test_render_actual_prompt(self, renderer):
        result = renderer.render("test_prompt", {"name": "World"})
        assert result is not None
        assert "World" in result

    def test_render_nonexistent_prompt(self, renderer):
        result = renderer.render("nonexistent_prompt_xyz", {})
        assert result is None

    def test_nested_template_structure(self, renderer):
        result = renderer.render_content(
            "{{#if items}}{{#each items}}{{name}}: {{#if active}}active{{/if}}{{/each}}{{/if}}",
            {"items": [{"name": "X", "active": True}, {"name": "Y", "active": False}]},
        )
        assert "X: active" in result
        assert "Y:" in result
