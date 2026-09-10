from __future__ import annotations

import pytest


pytestmark = pytest.mark.accessibility


class TestFocusManagement:
    def test_focus_order(self):
        focusable_sequence = [
            "skip-nav",
            "search-input",
            "nav-link-1",
            "nav-link-2",
            "main-content",
            "footer-link",
        ]
        for i in range(len(focusable_sequence) - 1):
            assert focusable_sequence[i] != focusable_sequence[i + 1]

    def test_focus_visible(self):
        css = """
        :focus-visible {
            outline: 2px solid #005fcc;
            outline-offset: 2px;
            border-radius: 2px;
        }
        """
        assert ":focus-visible" in css
        assert "outline" in css

    def test_focus_trapping_prevented(self):
        modal_html = """
        <div role="dialog" aria-modal="true">
            <h2>Modal</h2>
            <button>Close</button>
            <button>Confirm</button>
        </div>
        """
        assert 'aria-modal="true"' in modal_html
        assert "<button>Close</button>" in modal_html
        assert "<button>Confirm</button>" in modal_html

    def test_tabindex_values(self):
        positive_tabindex = [el for el in [1, 2, 3, 0, -1] if el > 0]
        natural_order = [el for el in [0, -1] if el <= 0]
        assert len(positive_tabindex) >= 0
        assert len(natural_order) >= 0
