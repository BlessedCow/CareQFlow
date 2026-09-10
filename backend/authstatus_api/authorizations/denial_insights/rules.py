from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuleThresholds:
    minimum_sample_size: int = 5
    minimum_denial_rate: float = 0.20
    minimum_relative_increase: float = 0.25


def _validate_rate(
    value: float,
    field_name: str,
) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{field_name} must be between 0 and 1.")


def validate_thresholds(
    thresholds: RuleThresholds,
) -> None:
    if thresholds.minimum_sample_size < 1:
        raise ValueError("minimum_sample_size must be at least 1.")

    _validate_rate(
        thresholds.minimum_denial_rate,
        "minimum_denial_rate",
    )

    if thresholds.minimum_relative_increase < 0:
        raise ValueError("minimum_relative_increase cannot be negative.")


def relative_rate_increase(
    observed_rate: float | None,
    baseline_rate: float | None,
) -> float | None:
    if observed_rate is None or baseline_rate is None:
        return None

    _validate_rate(
        observed_rate,
        "observed_rate",
    )
    _validate_rate(
        baseline_rate,
        "baseline_rate",
    )

    if baseline_rate == 0:
        if observed_rate == 0:
            return 0.0

        return None

    return round(
        (observed_rate - baseline_rate) / baseline_rate,
        4,
    )


def absolute_rate_difference(
    observed_rate: float | None,
    baseline_rate: float | None,
) -> float | None:
    if observed_rate is None or baseline_rate is None:
        return None

    _validate_rate(
        observed_rate,
        "observed_rate",
    )
    _validate_rate(
        baseline_rate,
        "baseline_rate",
    )

    return round(
        observed_rate - baseline_rate,
        4,
    )


def evaluate_denial_pattern(
    group: dict[str, Any],
    baseline: dict[str, Any],
    *,
    thresholds: RuleThresholds | None = None,
) -> dict[str, Any]:
    active_thresholds = thresholds or RuleThresholds()

    validate_thresholds(active_thresholds)

    decision_count = int(group.get("decision_count") or 0)
    baseline_count = int(baseline.get("decision_count") or 0)

    observed_rate = group.get("observed_denial_rate")
    baseline_rate = baseline.get("observed_denial_rate")

    if observed_rate is not None:
        observed_rate = float(observed_rate)

    if baseline_rate is not None:
        baseline_rate = float(baseline_rate)

    relative_increase = relative_rate_increase(
        observed_rate,
        baseline_rate,
    )

    absolute_difference = absolute_rate_difference(
        observed_rate,
        baseline_rate,
    )

    group_has_sample = decision_count >= active_thresholds.minimum_sample_size
    baseline_has_sample = baseline_count >= active_thresholds.minimum_sample_size

    meets_rate_threshold = (
        observed_rate is not None
        and observed_rate >= active_thresholds.minimum_denial_rate
    )

    if baseline_rate == 0 and observed_rate is not None:
        exceeds_baseline = observed_rate > 0
    else:
        exceeds_baseline = (
            relative_increase is not None
            and relative_increase >= active_thresholds.minimum_relative_increase
        )

    triggered = (
        group_has_sample
        and baseline_has_sample
        and meets_rate_threshold
        and exceeds_baseline
    )

    return {
        "triggered": triggered,
        "dimensions": dict(group.get("dimensions") or {}),
        "decision_count": decision_count,
        "baseline_decision_count": baseline_count,
        "observed_denial_rate": observed_rate,
        "baseline_denial_rate": baseline_rate,
        "absolute_rate_difference": absolute_difference,
        "relative_rate_increase": relative_increase,
        "minimum_sample_size": (active_thresholds.minimum_sample_size),
        "minimum_denial_rate": (active_thresholds.minimum_denial_rate),
        "minimum_relative_increase": (active_thresholds.minimum_relative_increase),
        "reason": _evaluation_reason(
            triggered=triggered,
            group_has_sample=group_has_sample,
            baseline_has_sample=baseline_has_sample,
            meets_rate_threshold=meets_rate_threshold,
            exceeds_baseline=exceeds_baseline,
            baseline_rate=baseline_rate,
            observed_rate=observed_rate,
        ),
    }


def _evaluation_reason(
    *,
    triggered: bool,
    group_has_sample: bool,
    baseline_has_sample: bool,
    meets_rate_threshold: bool,
    exceeds_baseline: bool,
    baseline_rate: float | None,
    observed_rate: float | None,
) -> str:
    if triggered:
        return (
            "Observed denial rate exceeds the selected baseline "
            "and meets the configured evidence thresholds."
        )

    if not group_has_sample:
        return "Group sample size is below the configured minimum."

    if not baseline_has_sample:
        return "Baseline sample size is below the configured minimum."

    if observed_rate is None:
        return "Observed denial rate is unavailable."

    if baseline_rate is None:
        return "Baseline denial rate is unavailable."

    if not meets_rate_threshold:
        return "Observed denial rate is below the configured rate threshold."

    if not exceeds_baseline:
        return (
            "Observed denial rate does not exceed the selected baseline "
            "by the configured amount."
        )

    return "The pattern does not meet the configured evidence thresholds."


def evaluate_groups_against_baseline(
    groups: list[dict[str, Any]],
    baseline: dict[str, Any],
    *,
    thresholds: RuleThresholds | None = None,
    triggered_only: bool = False,
) -> list[dict[str, Any]]:
    evaluations = [
        evaluate_denial_pattern(
            group,
            baseline,
            thresholds=thresholds,
        )
        for group in groups
    ]

    if triggered_only:
        evaluations = [
            evaluation for evaluation in evaluations if evaluation["triggered"]
        ]

    return evaluations
