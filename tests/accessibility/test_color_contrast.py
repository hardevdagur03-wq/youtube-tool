from __future__ import annotations

import pytest


pytestmark = pytest.mark.accessibility


def relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color1: str, color2: str) -> float:
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class TestColorContrast:
    def test_text_contrast_ratio(self):
        ratio = contrast_ratio("#000000", "#FFFFFF")
        assert ratio >= 7.0, (
            f"Black on white contrast {ratio:.1f}:1 below 7:1 (AAA)"
        )

    def test_large_text_contrast(self):
        ratio = contrast_ratio("#333333", "#FFFFFF")
        assert ratio >= 3.0, (
            f"Dark gray on white contrast {ratio:.1f}:1 below 3:1 (AA large)"
        )

    def test_ui_component_contrast(self):
        ratio = contrast_ratio("#007BFF", "#FFFFFF")
        assert ratio >= 3.0, (
            f"Blue on white contrast {ratio:.1f}:1 below 3:1 (AA for UI)"
        )

    @pytest.mark.parametrize("fg,bg,min_ratio", [
        ("#000000", "#FFFFFF", 7.0),
        ("#333333", "#FFFFFF", 4.5),
        ("#555555", "#FFFFFF", 3.0),
        ("#111111", "#F5F5F5", 7.0),
        ("#0066CC", "#FFFFFF", 3.0),
    ])
    def test_contrast_ratios(self, fg, bg, min_ratio):
        ratio = contrast_ratio(fg, bg)
        assert ratio >= min_ratio, (
            f"Contrast {ratio:.1f}:1 between {fg} and {bg} below {min_ratio}:1"
        )
