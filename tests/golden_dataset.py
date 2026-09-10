"""Golden dataset management for regression and benchmark testing."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class GoldenTestItem:
    """A single golden test case with expected outputs.

    Attributes
    ----------
    id : str
        Unique identifier for this test item.
    name : str
        Human-readable test name.
    category : str
        Logical category (e.g. ``"seo", "outline", "draft"``).
    video_url : str
        YouTube video URL used as input.
    input_data : dict
        Full input payload passed to the pipeline stage.
    expected_scores : dict
        Expected metric scores (SEO, grammar, readability, etc.).
    expected_entities : list
        Expected named entities in the output.
    expected_keywords : list
        Expected keyword phrases.
    expected_outline : dict
        Expected outline structure (title, headings, etc.).
    expected_sections : list
        Expected section content items.
    expected_seo_score : float
        Expected overall SEO score (0-100).
    expected_readability : float
        Expected readability score (0-100).
    expected_grammar : float
        Expected grammar score (0-100).
    """

    id: str
    name: str
    category: str
    video_url: str
    input_data: dict = field(default_factory=dict)
    expected_scores: dict = field(default_factory=dict)
    expected_entities: list = field(default_factory=list)
    expected_keywords: list = field(default_factory=list)
    expected_outline: dict = field(default_factory=dict)
    expected_sections: list = field(default_factory=list)
    expected_seo_score: float = 0.0
    expected_readability: float = 0.0
    expected_grammar: float = 0.0


@dataclass
class ValidationResult:
    """Outcome of comparing an actual output against a golden item.

    Attributes
    ----------
    item_id : str
    passed : bool
    field_results : dict
        Per-field pass/fail booleans keyed by field name.
    errors : list[str]
        Human-readable descriptions of mismatches.
    overall_score : float
        Fraction of fields that passed (0-1).
    """

    item_id: str
    passed: bool
    field_results: dict[str, bool]
    errors: list[str]
    overall_score: float


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class GoldenDataset:
    """Manage a collection of golden test items persisted as JSON files.

    Each item is stored as a separate JSON file under *base_dir* /
    ``{category}/{item_id}.json``.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        """Initialise the dataset store.

        Parameters
        ----------
        base_dir : str, optional
            Root directory for golden output files.  Defaults to
            ``tests/golden_outputs``.
        """
        if base_dir is None:
            base_dir = str(Path(__file__).resolve().parent / "golden_outputs")
        self._base = Path(base_dir)

    # -- Public API -----------------------------------------------------------

    def load(self, category: str | None = None) -> list[GoldenTestItem]:
        """Load golden items, optionally filtered by category.

        Parameters
        ----------
        category : str, optional
            If provided, only items in this category are returned.

        Returns
        -------
        list[GoldenTestItem]
        """
        items: list[GoldenTestItem] = []
        search_root = self._base / category if category else self._base
        if not search_root.is_dir():
            return items

        for p in sorted(search_root.rglob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                items.append(GoldenTestItem(**data))
            except (json.JSONDecodeError, TypeError) as exc:
                msg = f"Skipping {p}: {exc}"
                import warnings

                warnings.warn(msg)
        return items

    def save(self, item: GoldenTestItem) -> None:
        """Persist a golden item to disk.

        Parameters
        ----------
        item : GoldenTestItem
        """
        category_dir = self._base / item.category
        category_dir.mkdir(parents=True, exist_ok=True)
        file_path = category_dir / f"{item.id}.json"
        file_path.write_text(
            json.dumps(asdict(item), indent=2, default=str), encoding="utf-8"
        )

    def compare(self, actual: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
        """Deep-compare two dictionaries and return field-level diffs.

        Parameters
        ----------
        actual : dict
            Current pipeline output.
        expected : dict
            Expected golden output.

        Returns
        -------
        dict
            A dictionary with keys ``"identical"`` (bool), ``"diffs"`` (list),
            and ``"fields_compared"`` (int).
        """
        diffs: list[dict] = []
        all_keys = set(actual) | set(expected)

        for k in sorted(all_keys):
            a = actual.get(k)
            e = expected.get(k)
            if a != e:
                diffs.append(
                    {
                        "field": k,
                        "actual": _serialize(a),
                        "expected": _serialize(e),
                    }
                )

        return {
            "identical": len(diffs) == 0,
            "diffs": diffs,
            "fields_compared": len(all_keys),
        }

    def validate(
        self,
        item: GoldenTestItem,
        actual_output: dict[str, Any],
    ) -> ValidationResult:
        """Validate an actual output against a golden item.

        Parameters
        ----------
        item : GoldenTestItem
            The reference test item.
        actual_output : dict
            The output produced by the current pipeline.

        Returns
        -------
        ValidationResult
        """
        expected = asdict(item)
        field_results: dict[str, bool] = {}
        errors: list[str] = []

        for field in (
            "expected_scores",
            "expected_entities",
            "expected_keywords",
            "expected_outline",
            "expected_sections",
            "expected_seo_score",
            "expected_readability",
            "expected_grammar",
        ):
            actual_val = actual_output.get(field.lstrip("expected_").lstrip("expected_"), actual_output.get(field))
            if actual_val is None:
                # Try the actual key name directly
                actual_val = actual_output.get(field, None)

            expected_val = getattr(item, field)
            match = actual_val == expected_val
            field_results[field] = match
            if not match:
                actual_str = _serialize(actual_val)
                expected_str = _serialize(expected_val)
                errors.append(
                    f"{field}: expected {expected_str}, got {actual_str}"
                )

        overall_score = sum(1 for v in field_results.values() if v) / max(len(field_results), 1)
        return ValidationResult(
            item_id=item.id,
            passed=overall_score == 1.0,
            field_results=field_results,
            errors=errors,
            overall_score=overall_score,
        )

    def get_benchmark(self, category: str) -> list[GoldenTestItem]:
        """Alias for ``load(category=category)`` to match benchmark terminology.

        Parameters
        ----------
        category : str

        Returns
        -------
        list[GoldenTestItem]
        """
        return self.load(category=category)

    def register(self, item: GoldenTestItem) -> None:
        """Register (persist) a new golden item.

        This is an alias for :meth:`save` so that the API reads naturally:
        ``dataset.register(item)``.

        Parameters
        ----------
        item : GoldenTestItem
        """
        self.save(item)

    def list_categories(self) -> list[str]:
        """Return all category names that exist in the golden output store.

        Returns
        -------
        list[str]
        """
        if not self._base.is_dir():
            return []
        return sorted(
            d.name
            for d in self._base.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    def summary(self) -> dict[str, Any]:
        """Produce a summary of the golden dataset.

        Returns
        -------
        dict
            Keys: ``"total_items"``, ``"per_category"`` (dict mapping category
            name to item count), and ``"categories"`` (list).
        """
        cats = self.list_categories()
        per_cat: dict[str, int] = {}
        for cat in cats:
            items = self.load(category=cat)
            per_cat[cat] = len(items)

        return {
            "total_items": sum(per_cat.values()),
            "per_category": per_cat,
            "categories": cats,
        }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class GoldenOutputValidator:
    """Fine-grained validation helpers for golden output comparisons."""

    @staticmethod
    def validate_seo_score(
        actual: float,
        expected: float,
        tolerance: float = 5.0,
    ) -> bool:
        """Check that the actual SEO score is within *tolerance* of expected.

        Parameters
        ----------
        actual : float
        expected : float
        tolerance : float
            Maximum absolute difference.

        Returns
        -------
        bool
        """
        return abs(actual - expected) <= tolerance

    @staticmethod
    def validate_entities(
        actual: list[str],
        expected: list[str],
        min_overlap: float = 0.8,
    ) -> bool:
        """Check that the set overlap of entities meets *min_overlap*.

        Overlap is computed as ``2 * |intersection| / (|A| + |B|)`` (Sørensen-Dice).

        Parameters
        ----------
        actual : list[str]
        expected : list[str]
        min_overlap : float
            Minimum Sørensen-Dice coefficient (default 0.8).

        Returns
        -------
        bool
        """
        set_a = set(actual)
        set_b = set(expected)
        if not set_a and not set_b:
            return True
        intersection = set_a & set_b
        dice = 2.0 * len(intersection) / (len(set_a) + len(set_b))
        return dice >= min_overlap

    @staticmethod
    def validate_keywords(
        actual: list[str],
        expected: list[str],
        min_overlap: float = 0.7,
    ) -> bool:
        """Check that the set overlap of keywords meets *min_overlap*.

        Uses the same Sørensen-Dice coefficient as :meth:`validate_entities`.

        Parameters
        ----------
        actual : list[str]
        expected : list[str]
        min_overlap : float
            Minimum Sørensen-Dice coefficient (default 0.7).

        Returns
        -------
        bool
        """
        return GoldenOutputValidator.validate_entities(actual, expected, min_overlap)

    @staticmethod
    def validate_outline_structure(
        actual: dict[str, Any],
        expected: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare outline structure fields and return detailed results.

        Parameters
        ----------
        actual : dict
        expected : dict

        Returns
        -------
        dict
            Keys: ``"valid"`` (bool), ``"missing_keys"`` (list),
            ``"extra_keys"`` (list), ``"value_diffs"`` (list).
        """
        actual_keys = set(actual.keys())
        expected_keys = set(expected.keys())
        missing_keys = sorted(expected_keys - actual_keys)
        extra_keys = sorted(actual_keys - expected_keys)
        value_diffs: list[dict] = []

        for k in sorted(expected_keys & actual_keys):
            if actual[k] != expected[k]:
                value_diffs.append(
                    {
                        "key": k,
                        "actual": _serialize(actual[k]),
                        "expected": _serialize(expected[k]),
                    }
                )

        return {
            "valid": not missing_keys and not extra_keys and not value_diffs,
            "missing_keys": missing_keys,
            "extra_keys": extra_keys,
            "value_diffs": value_diffs,
        }

    @staticmethod
    def validate_section_quality(
        actual: list[dict],
        expected: list[dict],
    ) -> dict[str, Any]:
        """Compare section lists and return per-section validation results.

        Parameters
        ----------
        actual : list[dict]
        expected : list[dict]

        Returns
        -------
        dict
            Keys: ``"valid"`` (bool), ``"count_match"`` (bool),
            ``"section_results"`` (list of per-section dicts).
        """
        count_match = len(actual) == len(expected)
        section_results: list[dict] = []

        for i, (a_sec, e_sec) in enumerate(zip(actual, expected)):
            sec_result = GoldenOutputValidator.validate_outline_structure(a_sec, e_sec)
            sec_result["index"] = i
            section_results.append(sec_result)

        all_valid = count_match and all(sr["valid"] for sr in section_results)
        return {
            "valid": all_valid,
            "count_match": count_match,
            "section_results": section_results,
        }

    @staticmethod
    def full_validation(
        actual: dict[str, Any],
        expected: dict[str, Any],
    ) -> dict[str, Any]:
        """Run all validation checks and return a consolidated result.

        Parameters
        ----------
        actual : dict
        expected : dict

        Returns
        -------
        dict
            Composite result with individual check outcomes.
        """
        seo_pass = GoldenOutputValidator.validate_seo_score(
            actual.get("seo_score", 0), expected.get("expected_seo_score", 0)
        )
        entities_pass = GoldenOutputValidator.validate_entities(
            actual.get("entities", []), expected.get("expected_entities", [])
        )
        keywords_pass = GoldenOutputValidator.validate_keywords(
            actual.get("keywords", []), expected.get("expected_keywords", [])
        )
        outline_result = GoldenOutputValidator.validate_outline_structure(
            actual.get("outline", {}), expected.get("expected_outline", {})
        )
        sections_result = GoldenOutputValidator.validate_section_quality(
            actual.get("sections", []), expected.get("expected_sections", [])
        )

        return {
            "seo_score_pass": seo_pass,
            "entities_pass": entities_pass,
            "keywords_pass": keywords_pass,
            "outline_valid": outline_result["valid"],
            "sections_valid": sections_result["valid"],
            "overall_pass": all(
                [seo_pass, entities_pass, keywords_pass, outline_result["valid"], sections_result["valid"]]
            ),
            "details": {
                "outline": outline_result,
                "sections": sections_result,
            },
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _serialize(value: Any) -> str:
    """Convert *value* to a stable JSON string for comparison."""
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(value)
