"""Data models for the grade tracking system.

Defines the core data structures that flow between components:
parser -> grades.json -> alerter/dashboard.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Assignment:
    """A single graded assignment."""

    date: str
    name: str
    letter_grade: str
    points_earned: float
    points_possible: float
    percentage: float
    is_missing: bool
    is_exempt: bool
    is_not_included: bool
    is_not_yet_graded: bool


@dataclass
class Course:
    """A single course with its assignments."""

    name: str
    period: str
    instructor: str
    overall_grade: str
    assignments: list[Assignment] = field(default_factory=list)


@dataclass
class GradeReport:
    """Complete grade report for a student."""

    last_updated: str
    student: str
    grading_period: str
    courses: list[Course] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GradeReport:
        """Create a GradeReport from a plain dictionary."""
        courses = [
            Course(
                name=c["name"],
                period=c["period"],
                instructor=c["instructor"],
                overall_grade=c["overall_grade"],
                assignments=[Assignment(**a) for a in c.get("assignments", [])],
            )
            for c in data.get("courses", [])
        ]
        return cls(
            last_updated=data["last_updated"],
            student=data["student"],
            grading_period=data["grading_period"],
            courses=courses,
        )


@dataclass
class AlertState:
    """Tracks which missing assignments have already been alerted."""

    alerted_missing: list[str] = field(default_factory=list)
    last_run: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertState:
        """Create an AlertState from a plain dictionary."""
        return cls(
            alerted_missing=data.get("alerted_missing", []),
            last_run=data.get("last_run"),
        )


def assignment_key(course_name: str, assignment_name: str, date: str) -> str:
    """Build the unique key for an assignment.

    Format: ``{course_name}::{assignment_name}::{date}``
    """
    return f"{course_name}::{assignment_name}::{date}"
