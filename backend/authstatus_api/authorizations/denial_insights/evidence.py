from __future__ import annotations

import math
from typing import Any

WILSON_Z_95 = 1.959963984540054
FULL_SEPARATION_DIFFERENCE = 0.25

SAMPLE_MAX_POINTS = 40.0
SEPARATION_MAX_POINTS = 30.0
STABILITY_MAX_POINTS = 20.0
COMPLETENESS_MAX_POINTS = 10.0


def wilson_interval(
    denied_count: int,
    decision_count: int,
) -> tuple[float, float] | None:
    if decision_count <= 0:
        return None

    if denied_count < 0 or denied_count > decision_count:
        raise ValueError("denied_count must be between 0 and decision_count.")

    n = float(decision_count)
    proportion = denied_count / n
    z_squared = WILSON_Z_95**2

    denominator = 1 + (z_squared / n)

    center = (proportion + (z_squared / (2 * n))) / denominator

    margin = (
        WILSON_Z_95
        * math.sqrt((proportion * (1 - proportion) + (z_squared / (4 * n))) / n)
        / denominator
    )

    return (
        round(max(0.0, center - margin), 4),
        round(min(1.0, center + margin), 4),
    )


def _evidence_level(score: int) -> str:
    if score <= 24:
        return "Very weak"

    if score <= 49:
        return "Limited"

    if score <= 69:
        return "Moderate"

    if score <= 84:
        return "Strong"

    return "Very strong"


def _is_known_dimension(value: Any) -> bool:
    if value is None:
        return False

    normalized = str(value).strip()

    return bool(normalized and normalized.casefold() != "unknown")


def _completeness_ratio(
    group: dict[str, Any],
    dimensions: list[str],
) -> float:
    decision_count = int(group.get("decision_count") or 0)

    if decision_count <= 0:
        return 0.0

    dimension_values = dict(group.get("dimensions") or {})

    if dimensions:
        known_dimensions = sum(
            int(_is_known_dimension(dimension_values.get(dimension)))
            for dimension in dimensions
        )

        dimension_completeness = known_dimensions / len(dimensions)
    else:
        dimension_completeness = 1.0

    unclassified_count = int(group.get("unclassified_count") or 0)

    classification_completeness = max(
        0.0,
        min(
            1.0,
            1 - (unclassified_count / decision_count),
        ),
    )

    return (dimension_completeness + classification_completeness) / 2


def calculate_evidence_strength(
    group: dict[str, Any],
    evaluation: dict[str, Any],
    *,
    dimensions: list[str],
    preliminary_minimum: int = 5,
    standard_minimum: int = 20,
    include_calculation: bool = False,
) -> dict[str, Any]:
    if preliminary_minimum < 1:
        raise ValueError("preliminary_minimum must be at least 1.")

    if standard_minimum < preliminary_minimum:
        raise ValueError("standard_minimum cannot be lower than preliminary_minimum.")

    decision_count = int(group.get("decision_count") or 0)
    baseline_count = int(evaluation.get("baseline_decision_count") or 0)
    denied_count = int(group.get("denied_count") or 0)

    comparison_sample_size = min(
        decision_count,
        baseline_count,
    )

    sample_points = SAMPLE_MAX_POINTS * min(
        comparison_sample_size / standard_minimum,
        1.0,
    )

    absolute_difference = evaluation.get("absolute_rate_difference")

    if absolute_difference is None:
        separation_points = 0.0
    else:
        separation_points = SEPARATION_MAX_POINTS * min(
            abs(float(absolute_difference)) / FULL_SEPARATION_DIFFERENCE,
            1.0,
        )

    interval = wilson_interval(
        denied_count,
        decision_count,
    )

    if interval is None:
        stability_points = 0.0
        interval_width = None
    else:
        interval_width = interval[1] - interval[0]

        stability_points = STABILITY_MAX_POINTS * max(
            0.0,
            min(
                1.0,
                1 - interval_width,
            ),
        )

    completeness_ratio = _completeness_ratio(
        group,
        dimensions,
    )

    completeness_points = COMPLETENESS_MAX_POINTS * completeness_ratio

    uncapped_score = (
        sample_points + separation_points + stability_points + completeness_points
    )

    if comparison_sample_size < preliminary_minimum:
        sample_cap = 24
    elif comparison_sample_size < standard_minimum:
        sample_cap = 49
    else:
        sample_cap = 100

    score = min(
        int(round(uncapped_score)),
        sample_cap,
    )

    result: dict[str, Any] = {
        "score": score,
        "level": _evidence_level(score),
        "sample_size": decision_count,
        "baseline_sample_size": baseline_count,
        "wilson_95_interval": (
            {
                "lower": interval[0],
                "upper": interval[1],
            }
            if interval is not None
            else None
        ),
    }

    if include_calculation:
        result["calculation"] = {
            "version": "1.0",
            "sample_strength": {
                "points": round(
                    sample_points,
                    2,
                ),
                "maximum_points": SAMPLE_MAX_POINTS,
                "effective_sample_size": (comparison_sample_size),
                "standard_sample_size": (standard_minimum),
            },
            "baseline_separation": {
                "points": round(
                    separation_points,
                    2,
                ),
                "maximum_points": (SEPARATION_MAX_POINTS),
                "absolute_rate_difference": (absolute_difference),
                "full_points_difference": (FULL_SEPARATION_DIFFERENCE),
            },
            "rate_stability": {
                "points": round(
                    stability_points,
                    2,
                ),
                "maximum_points": (STABILITY_MAX_POINTS),
                "wilson_interval_width": (
                    round(
                        interval_width,
                        4,
                    )
                    if interval_width is not None
                    else None
                ),
            },
            "data_completeness": {
                "points": round(
                    completeness_points,
                    2,
                ),
                "maximum_points": (COMPLETENESS_MAX_POINTS),
                "ratio": round(
                    completeness_ratio,
                    4,
                ),
            },
            "uncapped_score": round(
                uncapped_score,
                2,
            ),
            "sample_cap": sample_cap,
            "final_score": score,
        }

    return result
