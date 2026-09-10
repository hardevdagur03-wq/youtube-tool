"""Benchmark Reporter — generates performance benchmark reports.

Creates structured HTML/JSON/Markdown reports from benchmark results.
Supports before/after comparison visualization.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from performance_engineering.models import BenchmarkResult

logger = logging.getLogger(__name__)


class BenchmarkReporter:
    """Generates performance benchmark reports in multiple formats."""

    @staticmethod
    def to_json(
        results: list[BenchmarkResult],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Generate a JSON benchmark report.

        Args:
            results: List of benchmark results.
            metadata: Optional metadata (timestamp, git commit, etc.).

        Returns:
            JSON string.
        """
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "scenarios": [r.model_dump() for r in results],
            "summary": BenchmarkReporter._summarize(results),
        }
        return json.dumps(report, indent=2, default=str)

    @staticmethod
    def to_markdown(results: list[BenchmarkResult]) -> str:
        """Generate a Markdown benchmark report.

        Args:
            results: List of benchmark results.

        Returns:
            Markdown string.
        """
        lines = [
            "# Performance Benchmark Report",
            f"Generated: {datetime.now(timezone.utc).isoformat()}\n",
            "## Summary",
            "| Scenario | Before (P95) | After (P95) | Improvement | Regression |",
            "|----------|-------------|-------------|-------------|------------|",
        ]

        for r in results:
            before_p95 = r.before.get(
                f"{r.scenario_name}_before_p95_ms",
                r.before.get(f"{r.scenario_name}_p95_ms", "N/A"),
            )
            after_p95 = r.after.get(
                f"{r.scenario_name}_after_p95_ms",
                r.after.get(f"{r.scenario_name}_p95_ms", "N/A"),
            )
            signal = "❌ REGRESSION" if r.regression else "✅ OK"
            lines.append(
                f"| {r.scenario_name} | {before_p95}ms | {after_p95}ms "
                f"| {r.improvement_pct:+.1f}% | {signal} |"
            )

        lines.append("")
        lines.append("## Detailed Results")
        for r in results:
            lines.append(f"\n### {r.scenario_name}")
            lines.append(f"- Improvement: {r.improvement_pct:+.1f}%")
            lines.append(f"- Regression: {r.regression}")
            lines.append("- Before:")
            for k, v in r.before.items():
                lines.append(f"  - {k}: {v}")
            lines.append("- After:")
            for k, v in r.after.items():
                lines.append(f"  - {k}: {v}")

        return "\n".join(lines)

    @staticmethod
    def to_html(results: list[BenchmarkResult]) -> str:
        """Generate an HTML benchmark report.

        Args:
            results: List of benchmark results.

        Returns:
            HTML string.
        """
        rows = ""
        for r in results:
            before_p95 = r.before.get(
                f"{r.scenario_name}_before_p95_ms",
                r.before.get(f"{r.scenario_name}_p95_ms", "N/A"),
            )
            after_p95 = r.after.get(
                f"{r.scenario_name}_after_p95_ms",
                r.after.get(f"{r.scenario_name}_p95_ms", "N/A"),
            )
            signal = "❌" if r.regression else "✅"
            color = "red" if r.regression else "green"
            rows += f"""
            <tr>
                <td>{r.scenario_name}</td>
                <td>{before_p95}ms</td>
                <td>{after_p95}ms</td>
                <td style="color: {color}">{r.improvement_pct:+.1f}% {signal}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html>
<head><title>Performance Benchmark Report</title>
<style>
    body {{ font-family: sans-serif; margin: 2em; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f5f5f5; }}
</style></head>
<body>
<h1>Performance Benchmark Report</h1>
<p>Generated: {datetime.now(timezone.utc).isoformat()}</p>
<table>
<tr><th>Scenario</th><th>Before (P95)</th><th>After (P95)</th><th>Improvement</th></tr>
{rows}
</table>
</body></html>"""

    @staticmethod
    def _summarize(results: list[BenchmarkResult]) -> dict[str, Any]:
        """Summarize benchmark results.

        Args:
            results: List of benchmark results.

        Returns:
            Summary dict.
        """
        improved = sum(1 for r in results if r.improvement_pct > 0)
        regressed = sum(1 for r in results if r.regression)
        return {
            "total_scenarios": len(results),
            "improved": improved,
            "regressed": regressed,
            "average_improvement_pct": round(
                sum(r.improvement_pct for r in results) / max(len(results), 1), 2
            ),
        }
