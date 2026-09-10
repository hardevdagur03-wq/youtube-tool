"""Report generation for coverage, regression, performance, benchmark, and quality data."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Enums & data types
# ---------------------------------------------------------------------------


class ReportType(str, Enum):
    """Categorisation of test report types."""

    COVERAGE = "coverage"
    REGRESSION = "regression"
    PERFORMANCE = "performance"
    BENCHMARK = "benchmark"
    SECURITY = "security"
    QUALITY = "quality"
    INTEGRATION = "integration"
    CONSOLIDATED = "consolidated"


@dataclass
class ReportSection:
    """A single section within a test report.

    Parameters
    ----------
    title : str
    content : str
        Markdown or plain-text content.
    data : dict | None
        Optional structured data.
    charts : list | None
        Optional chart configuration references.
    """

    title: str
    content: str
    data: dict | None = None
    charts: list | None = None


@dataclass
class TestReport:
    """Complete test report encompassing one or more domains.

    Attributes
    ----------
    title : str
    type : ReportType
    timestamp : str
        ISO-8601 formatted timestamp.
    summary : dict
        High-level pass/fail counts and aggregate metrics.
    sections : list[ReportSection]
    passed : bool
        Overall pass/fail status.
    artifacts : list[str]
        Paths to generated artifact files.
    """

    title: str
    type: ReportType
    timestamp: str
    summary: dict
    sections: list[ReportSection] = field(default_factory=list)
    passed: bool = True
    artifacts: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Factory that creates ``TestReport`` instances from various input data.

    Typical usage::

        gen = ReportGenerator()
        report = gen.generate_coverage_report({"overall": 94.2, ...})
        path = gen.export_html(report, "report.html")
    """

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialise the generator.

        Parameters
        ----------
        output_dir : str, optional
            Directory for exported report files.  Defaults to ``tests/reports``.
        """
        if output_dir is None:
            output_dir = str(Path(__file__).resolve().parent / "reports")
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # -- Report generation ---------------------------------------------------

    def generate_coverage_report(self, coverage_data: dict[str, Any]) -> TestReport:
        """Generate a coverage analysis report.

        Parameters
        ----------
        coverage_data : dict
            Expected keys: ``"overall"`` (float), ``"modules"`` (list of per-module
            dicts with ``module``, ``coverage_pct``, etc.).

        Returns
        -------
        TestReport
        """
        overall = coverage_data.get("overall", 0.0)
        modules = coverage_data.get("modules", [])
        low_coverage = [m for m in modules if m.get("coverage_pct", 100) < 80]

        sections = [
            ReportSection(
                title="Overall Coverage",
                content=f"Total line coverage: **{overall:.1f}%**",
                data={"overall_pct": overall},
            ),
            ReportSection(
                title="Module Breakdown",
                content=_format_table(
                    ["Module", "Coverage %", "Lines", "Covered", "Missing"],
                    [
                        [
                            m.get("module", "?"),
                            f"{m.get('coverage_pct', 0):.1f}",
                            str(m.get("total_lines", 0)),
                            str(m.get("covered_lines", 0)),
                            str(len(m.get("missing_lines", []))),
                        ]
                        for m in modules
                    ],
                ),
                data={"modules": modules},
            ),
        ]

        if low_coverage:
            sections.append(
                ReportSection(
                    title="Low Coverage Modules",
                    content="\n".join(
                        f"- {m['module']}: {m['coverage_pct']:.1f}%"
                        for m in low_coverage
                    ),
                    data={"low_coverage_modules": low_coverage},
                )
            )

        return TestReport(
            title="Coverage Report",
            type=ReportType.COVERAGE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary={"overall": overall, "modules_count": len(modules), "low_coverage_count": len(low_coverage)},
            sections=sections,
            passed=overall >= 80.0,
        )

    def generate_regression_report(self, regression_results: list[dict[str, Any]]) -> TestReport:
        """Generate a regression analysis report.

        Parameters
        ----------
        regression_results : list[dict]
            Each entry should have ``metric``, ``baseline``, ``current``,
            ``delta_pct``, ``passed``.

        Returns
        -------
        TestReport
        """
        passed = [r for r in regression_results if r.get("passed")]
        failed = [r for r in regression_results if not r.get("passed")]

        sections = [
            ReportSection(
                title="Regression Summary",
                content=(
                    f"**{len(passed)}** passed, **{len(failed)}** failed "
                    f"out of **{len(regression_results)}** metrics."
                ),
                data={"passed": len(passed), "failed": len(failed), "total": len(regression_results)},
            ),
        ]

        if failed:
            rows = [
                [r["metric"], f"{r['baseline']:.2f}", f"{r['current']:.2f}", f"{r['delta_pct']:.2f}%"]
                for r in failed
            ]
            sections.append(
                ReportSection(
                    title="Failed Regressions",
                    content=_format_table(["Metric", "Baseline", "Current", "Delta %"], rows),
                    data={"failed_regressions": failed},
                )
            )

        if passed:
            rows = [
                [r["metric"], f"{r['baseline']:.2f}", f"{r['current']:.2f}", f"{r['delta_pct']:.2f}%"]
                for r in passed
            ]
            sections.append(
                ReportSection(
                    title="Passed Regressions",
                    content=_format_table(["Metric", "Baseline", "Current", "Delta %"], rows),
                )
            )

        return TestReport(
            title="Regression Report",
            type=ReportType.REGRESSION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary={"total": len(regression_results), "passed": len(passed), "failed": len(failed)},
            sections=sections,
            passed=len(failed) == 0,
        )

    def generate_performance_report(self, perf_results: list[dict[str, Any]]) -> TestReport:
        """Generate a performance analysis report.

        Parameters
        ----------
        perf_results : list[dict]
            Each entry should have ``name``, ``duration_ms``, ``success``.

        Returns
        -------
        TestReport
        """
        total = len(perf_results)
        success_count = sum(1 for r in perf_results if r.get("success"))
        fail_count = total - success_count
        avg_duration = sum(r.get("duration_ms", 0) for r in perf_results) / max(total, 1)

        rows = [
            [
                r.get("name", "?"),
                f"{r.get('duration_ms', 0):.2f} ms",
                "✓" if r.get("success") else "✗",
            ]
            for r in perf_results
        ]

        sections = [
            ReportSection(
                title="Performance Summary",
                content=(
                    f"**{success_count}** succeeded, **{fail_count}** failed.  "
                    f"Average duration: **{avg_duration:.2f} ms**."
                ),
                data={"total": total, "success": success_count, "failed": fail_count, "avg_duration_ms": avg_duration},
            ),
            ReportSection(
                title="Detailed Results",
                content=_format_table(["Test", "Duration", "Status"], rows),
                data={"results": perf_results},
            ),
        ]

        return TestReport(
            title="Performance Report",
            type=ReportType.PERFORMANCE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary={"total": total, "passed": success_count, "failed": fail_count, "avg_duration_ms": avg_duration},
            sections=sections,
            passed=fail_count == 0,
        )

    def generate_benchmark_report(self, benchmark_results: list[dict[str, Any]]) -> TestReport:
        """Generate a benchmark report.

        Parameters
        ----------
        benchmark_results : list[dict]
            Each entry should have ``name``, ``category``, ``duration_ms``,
            ``success``.

        Returns
        -------
        TestReport
        """
        total = len(benchmark_results)
        success_count = sum(1 for r in benchmark_results if r.get("success"))
        fail_count = total - success_count

        rows = [
            [
                r.get("name", "?"),
                r.get("category", "?"),
                f"{r.get('duration_ms', 0):.2f} ms",
                "✓" if r.get("success") else "✗",
            ]
            for r in benchmark_results
        ]

        sections = [
            ReportSection(
                title="Benchmark Summary",
                content=f"**{success_count}** passed, **{fail_count}** failed.",
                data={"total": total, "passed": success_count, "failed": fail_count},
            ),
            ReportSection(
                title="Benchmark Results",
                content=_format_table(["Name", "Category", "Duration", "Status"], rows),
                data={"results": benchmark_results},
            ),
        ]

        return TestReport(
            title="Benchmark Report",
            type=ReportType.BENCHMARK,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary={"total": total, "passed": success_count, "failed": fail_count},
            sections=sections,
            passed=fail_count == 0,
        )

    def generate_security_report(self, security_results: list[dict[str, Any]]) -> TestReport:
        """Generate a security scan report.

        Parameters
        ----------
        security_results : list[dict]
            Each entry should have ``check``, ``passed``, ``findings``.

        Returns
        -------
        TestReport
        """
        passed_checks = sum(1 for r in security_results if r.get("passed"))
        failed_checks = sum(1 for r in security_results if not r.get("passed"))
        total_findings = sum(len(r.get("findings", [])) for r in security_results)

        rows = [
            [
                r.get("check", "?"),
                "✓" if r.get("passed") else "✗",
                str(len(r.get("findings", []))),
            ]
            for r in security_results
        ]

        sections = [
            ReportSection(
                title="Security Summary",
                content=(
                    f"**{passed_checks}** checks passed, **{failed_checks}** failed.  "
                    f"Total findings: **{total_findings}**."
                ),
                data={
                    "passed_checks": passed_checks,
                    "failed_checks": failed_checks,
                    "total_findings": total_findings,
                },
            ),
            ReportSection(
                title="Check Results",
                content=_format_table(["Check", "Passed", "Findings"], rows),
                data={"results": security_results},
            ),
        ]

        return TestReport(
            title="Security Report",
            type=ReportType.SECURITY,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary={"passed": passed_checks, "failed": failed_checks, "findings": total_findings},
            sections=sections,
            passed=failed_checks == 0,
        )

    def generate_quality_report(self, quality_gate_results: list[dict[str, Any]]) -> TestReport:
        """Generate a quality gate report.

        Parameters
        ----------
        quality_gate_results : list[dict]
            Each entry should have ``name``, ``passed``, ``score``, ``threshold``.

        Returns
        -------
        TestReport
        """
        passed = sum(1 for r in quality_gate_results if r.get("passed"))
        failed = sum(1 for r in quality_gate_results if not r.get("passed"))

        rows = [
            [
                r.get("name", "?"),
                "✓" if r.get("passed") else "✗",
                f"{r.get('score', 0):.2f}",
                f"{r.get('threshold', 0):.2f}",
            ]
            for r in quality_gate_results
        ]

        sections = [
            ReportSection(
                title="Quality Gate Summary",
                content=f"**{passed}** gates passed, **{failed}** failed.",
                data={"passed": passed, "failed": failed, "total": len(quality_gate_results)},
            ),
            ReportSection(
                title="Gate Results",
                content=_format_table(["Gate", "Passed", "Score", "Threshold"], rows),
                data={"results": quality_gate_results},
            ),
        ]

        return TestReport(
            title="Quality Gate Report",
            type=ReportType.QUALITY,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary={"passed": passed, "failed": failed, "total": len(quality_gate_results)},
            sections=sections,
            passed=failed == 0,
        )

    def generate_integration_report(self, integration_results: list[dict[str, Any]]) -> TestReport:
        """Generate an integration test report.

        Parameters
        ----------
        integration_results : list[dict]
            Each entry should have ``test``, ``passed``, ``duration_ms``.

        Returns
        -------
        TestReport
        """
        total = len(integration_results)
        passed_count = sum(1 for r in integration_results if r.get("passed"))
        failed_count = total - passed_count

        rows = [
            [r.get("test", "?"), "✓" if r.get("passed") else "✗", f"{r.get('duration_ms', 0):.2f} ms"]
            for r in integration_results
        ]

        sections = [
            ReportSection(
                title="Integration Test Summary",
                content=f"**{passed_count}** passed, **{failed_count}** failed.",
                data={"total": total, "passed": passed_count, "failed": failed_count},
            ),
            ReportSection(
                title="Test Results",
                content=_format_table(["Test", "Status", "Duration"], rows),
                data={"results": integration_results},
            ),
        ]

        return TestReport(
            title="Integration Test Report",
            type=ReportType.INTEGRATION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary={"total": total, "passed": passed_count, "failed": failed_count},
            sections=sections,
            passed=failed_count == 0,
        )

    def generate_consolidated_report(self, all_results: dict[str, Any]) -> TestReport:
        """Combine multiple sub-reports into a single consolidated report.

        Parameters
        ----------
        all_results : dict
            Mapping from report type to the corresponding data dictionary.
            Expected keys: ``"coverage"``, ``"regression"``, ``"performance"``,
            etc.

        Returns
        -------
        TestReport
        """
        sections: list[ReportSection] = []
        summary: dict[str, Any] = {"sub_reports": {}}
        overall_passed = True

        for report_type, data in all_results.items():
            sub_passed = data.get("passed", False)
            if not sub_passed:
                overall_passed = False
            summary["sub_reports"][report_type] = {
                "passed": sub_passed,
                "details": data.get("summary", data),
            }
            sections.append(
                ReportSection(
                    title=f"{report_type.title()} Report",
                    content=f"Status: {'PASS' if sub_passed else 'FAIL'}",
                    data=data,
                )
            )

        return TestReport(
            title="Consolidated Test Report",
            type=ReportType.CONSOLIDATED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            sections=sections,
            passed=overall_passed,
        )

    # -- Export --------------------------------------------------------------

    def export_html(self, report: TestReport, output_path: str | None = None) -> str:
        """Export a report as a styled HTML file.

        Parameters
        ----------
        report : TestReport
        output_path : str, optional
            Output file path.  Defaults to ``{report_dir}/{report_type}.html``.

        Returns
        -------
        str
            Absolute path to the generated file.
        """
        if output_path is None:
            output_path = str(self._output_dir / f"{report.type.value}_report.html")
        html = self._build_html_template(report)
        Path(output_path).write_text(html, encoding="utf-8")

        # Track artifact.
        report.artifacts.append(output_path)
        return os.path.abspath(output_path)

    def export_json(self, report: TestReport, output_path: str | None = None) -> str:
        """Export a report as a JSON file.

        Parameters
        ----------
        report : TestReport
        output_path : str, optional
            Defaults to ``{report_dir}/{report_type}.json``.

        Returns
        -------
        str
            Absolute path.
        """
        if output_path is None:
            output_path = str(self._output_dir / f"{report.type.value}_report.json")

        data = {
            "title": report.title,
            "type": report.type.value,
            "timestamp": report.timestamp,
            "summary": report.summary,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "data": s.data,
                    "charts": s.charts,
                }
                for s in report.sections
            ],
            "passed": report.passed,
            "artifacts": report.artifacts,
        }
        Path(output_path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

        report.artifacts.append(output_path)
        return os.path.abspath(output_path)

    def export_junit_xml(self, test_results: list[dict[str, Any]], output_path: str | None = None) -> str:
        """Export test results as a JUnit XML file.

        Parameters
        ----------
        test_results : list[dict]
            Each entry: ``{"name", "classname", "time", "failure", "error"}``.
        output_path : str, optional
            Defaults to ``{report_dir}/junit_report.xml``.

        Returns
        -------
        str
            Absolute path.
        """
        if output_path is None:
            output_path = str(self._output_dir / "junit_report.xml")

        lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<testsuites>',
            f'  <testsuite name="pytest" tests="{len(test_results)}" failures="0" errors="0">',
        ]

        for tr in test_results:
            name = tr.get("name", "unknown")
            classname = tr.get("classname", "")
            time_sec = tr.get("time", 0.0)
            failure = tr.get("failure")
            error = tr.get("error")

            if failure or error:
                msg = failure or error
                lines.append(
                    f'    <testcase classname="{classname}" name="{name}" '
                    f'time="{time_sec:.3f}">'
                )
                lines.append(f'      <failure message="{msg}"/>')
                lines.append(f'    </testcase>')
            else:
                lines.append(
                    f'    <testcase classname="{classname}" name="{name}" '
                    f'time="{time_sec:.3f}"/>'
                )

        lines.append('  </testsuite>')
        lines.append('</testsuites>')
        Path(output_path).write_text("\n".join(lines), encoding="utf-8")
        return os.path.abspath(output_path)

    def export_markdown(self, report: TestReport, output_path: str | None = None) -> str:
        """Export a report as Markdown.

        Parameters
        ----------
        report : TestReport
        output_path : str, optional
            Defaults to ``{report_dir}/{report_type}_report.md``.

        Returns
        -------
        str
            Absolute path.
        """
        if output_path is None:
            output_path = str(self._output_dir / f"{report.type.value}_report.md")

        lines: list[str] = [
            f"# {report.title}",
            "",
            f"**Type:** {report.type.value}",
            f"**Timestamp:** {report.timestamp}",
            f"**Status:** {'PASS' if report.passed else 'FAIL'}",
            "",
            "## Summary",
            "",
        ]

        for k, v in report.summary.items():
            lines.append(f"- **{k}**: {v}")

        lines.append("")
        for sec in report.sections:
            lines.append(f"## {sec.title}")
            lines.append("")
            lines.append(sec.content)
            lines.append("")

        Path(output_path).write_text("\n".join(lines), encoding="utf-8")
        report.artifacts.append(output_path)
        return os.path.abspath(output_path)

    # -- HTML template -------------------------------------------------------

    @staticmethod
    def _build_html_template(report: TestReport) -> str:
        """Build a full, self-contained HTML page with inline CSS styling.

        Parameters
        ----------
        report : TestReport

        Returns
        -------
        str
        """
        sections_html = ""
        for sec in report.sections:
            data_html = ""
            if sec.data:
                data_html = f"<pre>{json.dumps(sec.data, indent=2, default=str)}</pre>"
            sections_html += f"""
            <div class="section">
                <h2>{sec.title}</h2>
                <div class="content">{sec.content}</div>
                {data_html}
            </div>
            """

        status_color = "green" if report.passed else "red"
        summary_rows = "".join(
            f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in report.summary.items()
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{report.title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         max-width: 960px; margin: 2em auto; padding: 0 1em; color: #333; }}
  h1 {{ border-bottom: 2px solid {status_color}; padding-bottom: 0.3em; }}
  .status {{ font-size: 1.2em; font-weight: bold; color: {status_color}; }}
  .section {{ background: #f5f5f5; padding: 1em; margin: 1em 0; border-radius: 4px; }}
  .content {{ white-space: pre-wrap; }}
  pre {{ background: #eee; padding: 0.5em; overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 0.4em 0.6em; text-align: left; }}
  th {{ background: #e0e0e0; }}
  .artifacts {{ margin-top: 2em; font-size: 0.9em; color: #666; }}
</style>
</head>
<body>
<h1>{report.title}</h1>
<p class="status">{'PASS' if report.passed else 'FAIL'}</p>
<p>Type: {report.type.value} | Generated: {report.timestamp}</p>
<table><tr><th>Metric</th><th>Value</th></tr>{summary_rows}</table>
{sections_html}
<div class="artifacts"><p>Artifacts:</p><ul>
{"".join(f"<li>{a}</li>" for a in report.artifacts)}
</ul></div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format a simple Markdown table.

    Parameters
    ----------
    headers : list[str]
    rows : list[list[str]]

    Returns
    -------
    str
    """
    if not rows:
        return "*No data*"

    sep = "|" + "|".join("---" for _ in headers) + "|"
    header_line = "| " + " | ".join(headers) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return f"{header_line}\n{sep}\n{body}"
