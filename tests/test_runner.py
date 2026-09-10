"""Central test orchestrator that runs pytest suites programmatically."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import pytest

# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

TestRunResult = namedtuple(
    "TestRunResult",
    [
        "success",
        "total",
        "passed",
        "failed",
        "skipped",
        "duration",
        "report_path",
    ],
)
"""Aggregated outcome of a single test-suite execution.

Attributes
----------
success : bool
    True when *failed* is 0.
total : int
    Total number of collected tests.
passed : int
    Tests that passed.
failed : int
    Tests that failed.
skipped : int
    Tests that were skipped.
duration : float
    Wall-clock duration in seconds.
report_path : str
    Absolute path to the generated report file (empty string if none).
"""

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class TestRunner:
    """Orchestrate pytest runs and produce structured results.

    Usage::

        runner = TestRunner()
        result = runner.run_unit()
        print(result.success, result.duration)
    """

    _TEST_PATHS: dict[str, str | list[str]] = {
        "unit": str(Path(__file__).resolve().parent / "unit"),
        "integration": str(Path(__file__).resolve().parent / "integration"),
        "e2e": str(Path(__file__).resolve().parent / "e2e"),
        "regression": str(Path(__file__).resolve().parent / "regression"),
        "ai_regression": str(Path(__file__).resolve().parent / "ai_regression"),
        "performance": str(Path(__file__).resolve().parent / "performance"),
        "security": str(Path(__file__).resolve().parent / "security"),
        "chaos": str(Path(__file__).resolve().parent / "chaos"),
        "load": str(Path(__file__).resolve().parent / "load"),
        "stress": str(Path(__file__).resolve().parent / "stress"),
    }

    def __init__(self, report_dir: str | None = None) -> None:
        """Initialise the runner.

        Parameters
        ----------
        report_dir : str, optional
            Directory for generated reports.  Defaults to ``tests/reports``.
        """
        if report_dir is None:
            report_dir = str(Path(__file__).resolve().parent / "reports")
        self._report_dir = report_dir
        Path(self._report_dir).mkdir(parents=True, exist_ok=True)

    # -- Public entry points --------------------------------------------------

    def run_all(self, markers: str | None = None) -> TestRunResult:
        """Run every test in the project.

        Parameters
        ----------
        markers : str, optional
            pytest marker expression (e.g. ``"not slow"``).

        Returns
        -------
        TestRunResult
        """
        return self.execute(
            extra_args=[str(Path(__file__).resolve().parent.parent)],
            marker_expr=markers,
            report_name="full_suite",
        )

    def run_unit(self, markers: str | None = None) -> TestRunResult:
        """Run only unit tests (``tests/unit/``)."""
        return self._run_category("unit", markers)

    def run_integration(self, markers: str | None = None) -> TestRunResult:
        """Run integration tests (``tests/integration/``)."""
        return self._run_category("integration", markers)

    def run_e2e(self, markers: str | None = None) -> TestRunResult:
        """Run end-to-end tests (``tests/e2e/``)."""
        return self._run_category("e2e", markers)

    def run_regression(self, markers: str | None = None) -> TestRunResult:
        """Run regression tests (``tests/regression/``)."""
        return self._run_category("regression", markers)

    def run_ai_regression(self, markers: str | None = None) -> TestRunResult:
        """Run AI-regression tests (``tests/ai_regression/``)."""
        return self._run_category("ai_regression", markers)

    def run_performance(self, markers: str | None = None) -> TestRunResult:
        """Run performance / benchmark tests (``tests/performance/``)."""
        return self._run_category("performance", markers)

    def run_security(self, markers: str | None = None) -> TestRunResult:
        """Run security tests (``tests/security/``)."""
        return self._run_category("security", markers)

    def run_chaos(self, markers: str | None = None) -> TestRunResult:
        """Run chaos-engineering tests (``tests/chaos/``)."""
        return self._run_category("chaos", markers)

    def run_load(self, markers: str | None = None) -> TestRunResult:
        """Run load tests (``tests/load/``)."""
        return self._run_category("load", markers)

    def run_stress(self, markers: str | None = None) -> TestRunResult:
        """Run stress tests (``tests/stress/``)."""
        return self._run_category("stress", markers)

    # -- Coverage & quality gates --------------------------------------------

    def run_with_coverage(
        self,
        source_paths: list[str] | None = None,
        extra_args: list[str] | None = None,
        report_name: str = "coverage_run",
    ) -> TestRunResult:
        """Run tests with coverage collection via ``pytest-cov``.

        Parameters
        ----------
        source_paths : list[str], optional
            Package paths to measure.  Defaults to ``["database", "background_processing"]``.
        extra_args : list[str], optional
            Additional pytest flags.
        report_name : str
            Stem for the coverage report files.

        Returns
        -------
        TestRunResult
        """
        if source_paths is None:
            source_paths = ["database", "background_processing"]
        cov_args = []
        for src in source_paths:
            cov_args.extend(["--cov", src])
        cov_args.extend(
            [
                "--cov-report",
                f"xml:{self._report_dir}/{report_name}.xml",
                "--cov-report",
                f"html:{self._report_dir}/{report_name}_html",
                "--cov-report",
                "term-missing",
            ]
        )
        args = (extra_args or []) + cov_args
        return self.execute(extra_args=args, report_name=report_name)

    def run_quality_gates(self) -> dict[str, Any]:
        """Run quality-gate checks by invoking the quality gate module.

        Returns
        -------
        dict
            Serialised ``QualityGateResult`` entries keyed by gate name.
        """
        from tests.quality_gate import QualityGate

        runner = QualityGate()
        results: list[Any] = runner.evaluate_all({})
        return {r.name: {"passed": r.passed, "score": r.score, "threshold": r.threshold} for r in results}

    # -- Core execution engine -----------------------------------------------

    @staticmethod
    def execute(
        extra_args: list[str] | None = None,
        report_name: str = "pytest_report",
        report_dir: str | None = None,
        marker_expr: str | None = None,
        junit: bool = True,
    ) -> TestRunResult:
        """Run pytest programmatically and return a structured result.

        Parameters
        ----------
        extra_args : list[str], optional
            Additional CLI arguments forwarded to pytest.
        report_name : str
            Stem for report files.
        report_dir : str, optional
            Output directory for reports (defaults to ``tests/reports``).
        marker_expr : str, optional
            pytest ``-m`` marker expression.
        junit : bool
            Whether to produce a JUnit XML report.

        Returns
        -------
        TestRunResult
        """
        if report_dir is None:
            report_dir = str(Path(__file__).resolve().parent / "reports")
        Path(report_dir).mkdir(parents=True, exist_ok=True)

        args = ["--tb=short", "--strict-markers", "--color=yes"]
        if junit:
            args.extend(["--junitxml", os.path.join(report_dir, f"{report_name}.xml")])
        if marker_expr:
            args.extend(["-m", marker_expr])
        if extra_args:
            args.extend(extra_args)

        start = time.monotonic()
        exit_code = pytest.main(args)
        duration = time.monotonic() - start

        total = passed = failed = skipped = 0
        # Attempt to read outcome from a JUnit XML if it was generated.
        junit_path = os.path.join(report_dir, f"{report_name}.xml")
        if junit and os.path.isfile(junit_path):
            _total, _passed, _failed, _skipped = _parse_junit_counts(junit_path)
            if _total:
                total, passed, failed, skipped = _total, _passed, _failed, _skipped

        if not total:
            total = max(exit_code, 1)
            passed = total - exit_code if exit_code >= 0 else 0
            failed = exit_code if exit_code > 0 else 0

        report_path = junit_path if os.path.isfile(junit_path) else ""
        return TestRunResult(
            success=failed == 0,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=duration,
            report_path=report_path,
        )

    @staticmethod
    def parallel_execute(
        suites: Sequence[tuple[str, list[str] | None, str]],
        max_workers: int = 4,
    ) -> list[TestRunResult]:
        """Run multiple test suites in parallel via a thread pool.

        Parameters
        ----------
        suites :
            An iterable of ``(report_name, extra_args, marker_expr)`` tuples.
        max_workers : int
            Maximum number of concurrent pytest processes.

        Returns
        -------
        list[TestRunResult]
            Results in the same order as *suites*.
        """
        results: list[TestRunResult] = []

        def _run_one(suite: tuple[str, list[str] | None, str]) -> TestRunResult:
            name, args, markers = suite
            return TestRunner.execute(extra_args=args, report_name=name, marker_expr=markers)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            fut_map = {pool.submit(_run_one, s): s for s in suites}
            for fut in as_completed(fut_map):
                try:
                    results.append(fut.result())
                except Exception as exc:
                    suite_name = fut_map[fut][0]
                    results.append(
                        TestRunResult(
                            success=False,
                            total=0,
                            passed=0,
                            failed=1,
                            skipped=0,
                            duration=0.0,
                            report_path="",
                        )
                    )
                    sys.stderr.write(f"[TestRunner] suite {suite_name!r} failed: {exc}\n")

        return results

    # -- Formatting -----------------------------------------------------------

    @staticmethod
    def format_results(
        results: Sequence[TestRunResult],
        fmt: str = "json",
    ) -> str:
        """Format one or more ``TestRunResult`` entries.

        Parameters
        ----------
        results :
            One or more result namedtuples.
        fmt : {"json", "html", "junit"}
            Desired output format.  ``"junit"`` merges results into a pseudo-XML
            string.

        Returns
        -------
        str
            Formatted output.
        """
        data = [r._asdict() for r in results]

        if fmt == "json":
            return json.dumps(data, indent=2, default=str)

        if fmt == "html":
            parts = ["<html><body><h1>Test Results</h1><table border='1'>"]
            parts.append(
                "<tr><th>Success</th><th>Total</th><th>Passed</th>"
                "<th>Failed</th><th>Skipped</th><th>Duration (s)</th></tr>"
            )
            for r in results:
                parts.append(
                    f"<tr><td>{r.success}</td><td>{r.total}</td><td>{r.passed}</td>"
                    f"<td>{r.failed}</td><td>{r.skipped}</td><td>{r.duration:.2f}</td></tr>"
                )
            parts.append("</table></body></html>")
            return "\n".join(parts)

        if fmt == "junit":
            lines = ['<?xml version="1.0" encoding="utf-8"?>']
            lines.append('<testsuites>')
            for r in results:
                lines.append(
                    f'  <testsuite name="{r.report_path}" tests="{r.total}" '
                    f'failures="{r.failed}" skipped="{r.skipped}" time="{r.duration:.3f}">'
                )
                lines.append('  </testsuite>')
            lines.append('</testsuites>')
            return "\n".join(lines)

        msg = f"Unsupported format: {fmt!r} (choose json, html, junit)"
        raise ValueError(msg)

    # -- Internal helpers -----------------------------------------------------

    def _run_category(self, category: str, markers: str | None) -> TestRunResult:
        test_path = self._TEST_PATHS.get(category)
        if not test_path:
            raise ValueError(f"Unknown test category: {category}")
        return self.execute(
            extra_args=[test_path] if isinstance(test_path, str) else list(test_path),
            marker_expr=markers,
            report_name=f"{category}_suite",
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_junit_counts(xml_path: str) -> tuple[int, int, int, int]:
    """Naively parse a JUnit XML file for test counts."""
    total = passed = failed = skipped = 0
    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(xml_path)
        root = tree.getroot()
        for ts in root.iter("testsuite"):
            total += int(ts.get("tests", 0))
            failed += int(ts.get("failures", 0)) + int(ts.get("errors", 0))
            skipped += int(ts.get("skipped", 0))
        passed = total - failed - skipped
    except Exception:
        pass
    return total, passed, failed, skipped
