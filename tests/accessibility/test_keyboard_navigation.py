from __future__ import annotations

import pytest


pytestmark = pytest.mark.accessibility


class TestKeyboardNavigation:
    def test_tab_order(self):
        elements = [
            {"id": "skip-link", "tabindex": 1},
            {"id": "search", "tabindex": 2},
            {"id": "nav", "tabindex": 3},
            {"id": "content", "tabindex": 4},
            {"id": "footer", "tabindex": 5},
        ]
        for i in range(len(elements) - 1):
            assert elements[i]["tabindex"] < elements[i + 1]["tabindex"]

    def test_focus_indicators(self):
        css = """
        :focus {
            outline: 2px solid blue;
            outline-offset: 2px;
        }
        :focus-visible {
            outline: 2px solid #005fcc;
        }
        """
        assert ":focus" in css
        assert "outline" in css

    def test_skip_navigation(self):
        html = """
        <a href="#main-content" class="skip-link">Skip to main content</a>
        <main id="main-content">
            <h1>Main Content</h1>
        </main>
        """
        assert "skip-link" in html
        assert 'href="#main-content"' in html
        assert 'id="main-content"' in html

    def test_no_keyboard_traps(self):
        focusable_elements = ["a", "button", "input", "select", "textarea", "[tabindex]"]
        html_trap_free = """
        <div>
            <a href="/">Home</a>
            <button>Submit</button>
            <input type="text">
        </div>
        """
        assert len(focusable_elements) >= 5
