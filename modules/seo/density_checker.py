"""Density checker — Phase 8. Keyword density analysis with recommendations."""

from __future__ import annotations
from typing import Any


def check_density(text: str, keywords: list[str]) -> dict[str, Any]:
    wc = len(text.split())
    if wc == 0:
        return {"densities": {}, "recommendations": []}

    densities: dict[str, float] = {}
    recs: list[str] = []

    for kw in keywords:
        if not kw.strip():
            continue
        count = text.lower().count(kw.lower())
        density = round((count / wc) * 100, 2)
        densities[kw] = density
        if density > 3.0:
            recs.append(f"'{kw}' density {density}% > 3% — reduce usage")
        elif density < 0.3:
            recs.append(f"'{kw}' density {density}% < 0.3% — increase natural usage")

    return {"densities": densities, "recommendations": recs}
