from __future__ import annotations

from security.output_sanitizer import OutputSanitizer


class TestOutputSanitizer:
    def setup_method(self):
        self.sanitizer = OutputSanitizer()

    def test_sanitize_html_removes_scripts(self):
        result = self.sanitizer.sanitize_html("<script>alert('xss')</script><p>safe</p>")
        assert "<script>" not in result
        assert "<p>safe</p>" in result

    def test_sanitize_html_keeps_allowed_tags(self):
        result = self.sanitizer.sanitize_html("<h1>Title</h1><p>Paragraph</p><strong>Bold</strong>")
        assert "<h1>Title</h1>" in result
        assert "<strong>Bold</strong>" in result

    def test_sanitize_html_strips_disallowed_tags(self):
        result = self.sanitizer.sanitize_html("<marquee>bad</marquee><blink>bad</blink>")
        assert "<marquee>" not in result
        assert "<blink>" not in result

    def test_sanitize_html_strips_event_handlers(self):
        result = self.sanitizer.sanitize_html('<img src=x onerror=alert(1)>')
        assert "onerror" not in result

    def test_sanitize_markdown_removes_scripts(self):
        result = self.sanitizer.sanitize_markdown("hello <script>alert('xss')</script> world")
        assert "<script>" not in result

    def test_sanitize_markdown_strips_image_urls(self):
        result = self.sanitizer.sanitize_markdown("![img](http://evil.com/tracker)")
        assert "![" not in result

    def test_sanitize_markdown_keeps_links_stripped(self):
        result = self.sanitizer.sanitize_markdown("[click](http://evil.com)")
        assert "](http://evil.com)" not in result

    def test_sanitize_json_truncates_strings(self):
        result = self.sanitizer.sanitize_json("x" * 20000)
        assert len(result) == 10000

    def test_sanitize_json_truncates_lists(self):
        result = self.sanitizer.sanitize_json(list(range(2000)))
        assert len(result) == 1000

    def test_sanitize_json_limits_depth(self):
        deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": {"j": {"k": "deep"}}}}}}}}}}}
        result = self.sanitizer.sanitize_json(deep)
        assert isinstance(result, dict)

    def test_sanitize_error_message_redacts_api_key(self):
        result = self.sanitizer.sanitize_error_message("api_key=sk-1234567890abcdef")
        assert "sk-1234567890abcdef" not in result
        assert "api_key=***" in result

    def test_sanitize_error_message_redacts_email(self):
        result = self.sanitizer.sanitize_error_message("user@example.com")
        assert "[EMAIL]" in result

    def test_sanitize_error_message_truncates_long(self):
        long_msg = "A" * 3000
        result = self.sanitizer.sanitize_error_message(long_msg)
        assert len(result) <= 2000

    def test_sanitize_filename_replaces_special_chars(self):
        result = self.sanitizer.sanitize_filename('file<>:"/\\|?*.txt')
        assert all(c not in result for c in '<>:"/\\|?*')

    def test_sanitize_filename_prevents_path_traversal(self):
        result = self.sanitizer.sanitize_filename("../../etc/passwd")
        assert ".." not in result

    def test_sanitize_filename_collapses_spaces(self):
        result = self.sanitizer.sanitize_filename("my  file  name.txt")
        assert "  " not in result

    def test_sanitize_log_output_redacts_sensitive_keys(self):
        log_data = {"username": "joe", "password": "secret123", "api_key": "sk-test"}
        result = self.sanitizer.sanitize_log_output(log_data)
        assert result["password"] == "***REDACTED***"
        assert result["api_key"] == "***REDACTED***"
        assert result["username"] == "joe"

    def test_sanitize_log_output_truncates_long_values(self):
        log_data = {"data": "x" * 1000}
        result = self.sanitizer.sanitize_log_output(log_data)
        assert len(result["data"]) <= 500

    def test_sanitize_html_empty_string(self):
        assert self.sanitizer.sanitize_html("") == ""

    def test_sanitize_markdown_empty_string(self):
        assert self.sanitizer.sanitize_markdown("") == ""

    def test_sanitize_error_message_empty_string(self):
        assert self.sanitizer.sanitize_error_message("") == ""
