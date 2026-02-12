"""Discord alert logic with state tracking.

Compares current missing assignments against previously alerted state,
identifies new missing and resolved assignments, and sends Discord
webhook notifications.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from grade_data.models import AlertState, GradeReport, assignment_key

logger = logging.getLogger(__name__)


def find_missing_assignments(report: GradeReport) -> list[str]:
    """Find all missing assignment keys in a grade report.

    Args:
        report: The current grade report.

    Returns:
        List of assignment keys in ``course::name::date`` format.
    """
    missing: list[str] = []
    for course in report.courses:
        for a in course.assignments:
            if a.is_missing:
                missing.append(assignment_key(course.name, a.name, a.date))
    return missing


def find_new_missing(
    current_missing: list[str],
    state: AlertState,
) -> list[str]:
    """Identify missing assignments not yet alerted.

    Args:
        current_missing: Keys of currently missing assignments.
        state: The previous alert state.

    Returns:
        Keys of newly missing assignments.
    """
    already_alerted = set(state.alerted_missing)
    return [key for key in current_missing if key not in already_alerted]


def find_resolved_missing(
    current_missing: list[str],
    state: AlertState,
) -> list[str]:
    """Identify previously missing assignments that are now resolved.

    Args:
        current_missing: Keys of currently missing assignments.
        state: The previous alert state.

    Returns:
        Keys of resolved assignments.
    """
    current_set = set(current_missing)
    return [key for key in state.alerted_missing if key not in current_set]


def _parse_key(key: str) -> tuple[str, str, str]:
    """Parse an assignment key into course, name, and date.

    Args:
        key: Assignment key in ``course::name::date`` format.

    Returns:
        Tuple of (course_name, assignment_name, date).
    """
    parts = key.split("::")
    return parts[0], parts[1], parts[2]


def build_missing_embed(
    report: GradeReport,
    new_keys: list[str],
    still_outstanding: list[str],
    dashboard_url: str,
) -> dict[str, Any]:
    """Build a Discord embed payload for new missing assignments.

    Args:
        report: Current grade report (used for student name).
        new_keys: Keys of newly missing assignments.
        still_outstanding: Keys of previously alerted assignments still missing.
        dashboard_url: URL to the grade dashboard.

    Returns:
        Discord webhook payload dict with embeds list.
    """
    grouped: dict[str, list[tuple[str, str]]] = {}
    for key in new_keys:
        course, name, date = _parse_key(key)
        grouped.setdefault(course, []).append((name, date))

    lines: list[str] = []
    for course_name, assignments in grouped.items():
        lines.append(f"**{course_name}**")
        for name, date in assignments:
            lines.append(f"- {name} ({date})")

    if still_outstanding:
        count = len(still_outstanding)
        lines.append(f"\n{count} other missing")

    if dashboard_url:
        lines.append(f"\n[View Dashboard]({dashboard_url})")

    first_name = report.student.split()[0] if report.student else "Student"

    return {
        "embeds": [
            {
                "title": f"New Missing Assignments for {first_name}",
                "description": "\n".join(lines),
                "color": 0xFF0000,
            }
        ],
    }


def build_resolved_embed(
    student_name: str,
    resolved_keys: list[str],
    dashboard_url: str = "",
) -> dict[str, Any]:
    """Build a Discord embed payload for resolved assignments.

    Args:
        student_name: Name of the student.
        resolved_keys: Keys of assignments that are no longer missing.
        dashboard_url: URL to the grade dashboard.

    Returns:
        Discord webhook payload dict with embeds list.
    """
    lines: list[str] = []
    for key in resolved_keys:
        course, name, date = _parse_key(key)
        lines.append(f"- {name} ({course}, {date})")

    if dashboard_url:
        lines.append(f"\n[View Dashboard]({dashboard_url})")

    first_name = student_name.split()[0] if student_name else "Student"

    return {
        "embeds": [
            {
                "title": f"Assignments Completed for {first_name}",
                "description": "\n".join(lines),
                "color": 0x00FF00,
            }
        ],
    }


def _post_webhook(webhook_url: str, payload: dict[str, Any]) -> None:
    """Post a JSON payload to a Discord webhook URL.

    Args:
        webhook_url: The Discord webhook URL.
        payload: The JSON payload to send.
    """
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except requests.exceptions.RequestException:
        logger.exception("Failed to post to Discord webhook")


def send_alerts(
    grade_report: GradeReport,
    state: AlertState,
    webhook_url: str,
    dashboard_url: str,
) -> AlertState:
    """Compare missing assignments against state and send Discord alerts.

    Identifies new missing assignments and resolved assignments,
    sends appropriate Discord webhooks, and updates the alert state.

    Args:
        grade_report: Current grade report.
        state: Previous alert state.
        webhook_url: Discord webhook URL.
        dashboard_url: URL to the grade dashboard.

    Returns:
        Updated AlertState reflecting current missing assignments.
    """
    current_missing = find_missing_assignments(grade_report)
    new_missing = find_new_missing(current_missing, state)
    resolved = find_resolved_missing(current_missing, state)

    if new_missing:
        still_outstanding = [k for k in state.alerted_missing if k not in set(resolved)]
        embed_payload = build_missing_embed(
            grade_report, new_missing, still_outstanding, dashboard_url
        )
        _post_webhook(webhook_url, embed_payload)

    if resolved:
        resolved_payload = build_resolved_embed(
            grade_report.student, resolved, dashboard_url
        )
        _post_webhook(webhook_url, resolved_payload)

    updated_alerted = [key for key in state.alerted_missing if key not in set(resolved)]
    updated_alerted.extend(new_missing)

    return AlertState(
        alerted_missing=updated_alerted,
        last_run=datetime.now(UTC).isoformat(),
    )


def load_alert_state(path: str) -> AlertState:
    """Load alert state from a JSON file.

    Args:
        path: Path to the state JSON file.

    Returns:
        AlertState loaded from file, or empty state if file missing.
    """
    state_path = Path(path)
    if not state_path.exists():
        return AlertState()
    data = json.loads(state_path.read_text())
    return AlertState.from_dict(data)


def save_alert_state(state: AlertState, path: str) -> None:
    """Save alert state to a JSON file.

    Args:
        state: The alert state to persist.
        path: File path to write the JSON output.
    """
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state.to_dict(), indent=2) + "\n")
