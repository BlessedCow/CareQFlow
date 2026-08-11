from __future__ import annotations

from typing import Any

REQUEST_SUBMITTED_EVENT_TYPES = {
    "request submitted",
    "initial authorization",
}

TERMINAL_EVENT_TYPES = {
    "payer response",
    "peer review",
    "appeal",
}

TERMINAL_OUTCOMES = {
    "approved",
    "denied",
    "denied with peer review option",
    "more information needed",
    "no pa required",
    "appeal approved",
    "appeal denied",
    "upheld",
    "overturned",
    "completed",
    "discharged",
}


def normalize_event_label(value: Any) -> str:
    return str(value or "").strip().lower()


def event_datetime_value(event: dict[str, Any]) -> str:
    event_date = str(event.get("event_date") or "").strip()
    event_time = str(event.get("event_time") or "").strip()

    if not event_date:
        return ""

    if not event_time:
        return f"{event_date}T00:00:00"

    if len(event_time) == 5:
        return f"{event_date}T{event_time}:00"

    return f"{event_date}T{event_time}"


def is_request_submitted_event(
    event: dict[str, Any],
) -> bool:
    return (
        normalize_event_label(event.get("event_type")) in REQUEST_SUBMITTED_EVENT_TYPES
    )


def is_terminal_event(event: dict[str, Any]) -> bool:
    event_type = normalize_event_label(event.get("event_type"))
    outcome = normalize_event_label(event.get("outcome"))

    return event_type in TERMINAL_EVENT_TYPES or outcome in TERMINAL_OUTCOMES


def status_from_timeline_event(
    event: dict[str, Any],
) -> str | None:
    event_type = normalize_event_label(event.get("event_type"))
    outcome = normalize_event_label(event.get("outcome"))

    if event_type == "request submitted":
        return "Pending"

    if outcome in {
        "approved",
        "appeal approved",
        "overturned",
    }:
        return "Approved"

    if outcome in {
        "denied",
        "denied with peer review option",
        "appeal denied",
        "upheld",
    }:
        return "Denied"

    if event_type == "peer review" or outcome in {
        "scheduled",
        "peer review scheduled",
    }:
        return "P2P"

    if event_type == "appeal" or outcome in {"appeal pending", "pending"}:
        return "Appealed"

    if outcome == "no pa required":
        return "No PA Required"

    if outcome == "completed":
        return "Completed"

    if outcome == "discharged":
        return "Discharged"

    if outcome == "more information needed":
        return "Pending"

    return None


def timeline_status(
    events: list[dict[str, Any]],
) -> str:
    for event in reversed(events):
        outcome = normalize_event_label(event.get("outcome"))
        event_type = normalize_event_label(event.get("event_type"))

        if outcome == "completed" or event_type == "authorization complete":
            return "Completed"

        if outcome == "discharged" or event_type == "discharge":
            return "Discharged"

    for event in reversed(events):
        status = status_from_timeline_event(event)

        if status:
            return status

    return "Pending"


def latest_review_event(
    events: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for event in reversed(events):
        if (
            event.get("auth_start_date")
            or event.get("auth_end_date")
            or event.get("review_due_date")
            or int(event.get("requested_days") or 0) > 0
            or int(event.get("approved_days") or 0) > 0
        ):
            return event

    return None


def current_auth_snapshot(
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    latest_review = latest_review_event(events)
    status = timeline_status(events)

    return {
        "status": status,
        "requested_days": (
            latest_review.get("requested_days") if latest_review else None
        ),
        "approved_days": (
            latest_review.get("approved_days") if latest_review else None
        ),
        "auth_start_date": (
            latest_review.get("auth_start_date") if latest_review else None
        ),
        "auth_end_date": (
            latest_review.get("auth_end_date") if latest_review else None
        ),
        "review_due_date": (
            None
            if status
            in {
                "Completed",
                "Discharged",
                "No PA Required",
            }
            else latest_review.get("review_due_date") if latest_review else None
        ),
    }
