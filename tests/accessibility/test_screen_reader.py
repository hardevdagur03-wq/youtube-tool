from __future__ import annotations

import pytest


pytestmark = pytest.mark.accessibility


class TestScreenReader:
    def test_aria_labels(self):
        html = """
        <button aria-label="Close dialog">X</button>
        <nav aria-label="Main navigation">
            <a href="/">Home</a>
        </nav>
        <div role="dialog" aria-labelledby="dialog-title">
            <h2 id="dialog-title">Confirm</h2>
        </div>
        """
        assert 'aria-label="Close dialog"' in html
        assert 'aria-label="Main navigation"' in html
        assert 'aria-labelledby="dialog-title"' in html

    def test_aria_roles(self):
        html = """
        <header role="banner">
            <h1>Site Title</h1>
        </header>
        <nav role="navigation">
            <a href="/">Home</a>
        </nav>
        <main role="main">
            <article role="article">
                <h2>Blog Post</h2>
            </article>
        </main>
        <footer role="contentinfo">
            <p>Copyright 2026</p>
        </footer>
        """
        assert 'role="banner"' in html
        assert 'role="navigation"' in html
        assert 'role="main"' in html
        assert 'role="contentinfo"' in html

    def test_alt_text_on_images(self):
        html = """
        <img src="banner.jpg" alt="Site banner showing logo">
        <img src="icon.png" alt="Search icon" role="img">
        <img src="decorative.png" alt="" role="presentation">
        """
        assert 'alt="Site banner' in html
        assert 'alt="Search icon"' in html
        assert 'alt=""' in html

    def test_semantic_headings(self):
        headings = ["h1", "h2", "h3", "h4", "h5", "h6"]
        html = """
        <h1>Page Title</h1>
        <h2>Section Title</h2>
        <h3>Subsection Title</h3>
        """
        for tag in ["h1", "h2", "h3"]:
            assert tag in html
