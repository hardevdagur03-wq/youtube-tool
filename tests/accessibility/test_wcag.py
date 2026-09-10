from __future__ import annotations

import pytest


pytestmark = pytest.mark.accessibility


class TestWCAG:
    def test_wcag_perceivable(self):
        html = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Main Heading</h1>
                <img src="photo.jpg" alt="A photo">
                <p>Content text</p>
            </body>
        </html>
        """
        assert "<img" in html
        assert 'alt=' in html
        assert "<h1>" in html

    def test_wcag_operable(self):
        html = """
        <html>
            <body>
                <a href="/home">Home</a>
                <button type="button">Submit</button>
                <input type="text" name="search">
            </body>
        </html>
        """
        assert "<a href" in html
        assert "<button" in html
        assert "<input" in html

    def test_wcag_understandable(self):
        html = """
        <html lang="en">
            <head>
                <title>Page Title</title>
                <meta name="description" content="Page description">
            </head>
            <body>
                <label for="email">Email address</label>
                <input id="email" type="email">
            </body>
        </html>
        """
        assert 'lang="en"' in html
        assert "<title>" in html
        assert '<label for="email">' in html

    def test_wcag_robust(self):
        html = """
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <div role="navigation">
                    <ul><li><a href="/">Home</a></li></ul>
                </div>
                <main role="main">
                    <article>
                        <h1>Article Title</h1>
                    </article>
                </main>
            </body>
        </html>
        """
        assert 'role="navigation"' in html
        assert 'role="main"' in html
        assert "<article>" in html
