"""Tests for grade_data.models module."""

import json

from grade_data.models import (
    AlertState,
    Assignment,
    Course,
    GradeReport,
    assignment_key,
)


class TestAssignment:
    """Tests for the Assignment dataclass."""

    def test_create_assignment_with_all_fields(self) -> None:
        """Test creating an Assignment with all required fields."""
        assignment = Assignment(
            date="2026-01-12",
            name="5.3.4 Lesson",
            letter_grade="A",
            points_earned=5.0,
            points_possible=5.0,
            percentage=100.0,
            is_missing=False,
            is_exempt=False,
            is_not_included=False,
            is_not_yet_graded=False,
        )
        assert assignment.date == "2026-01-12"
        assert assignment.name == "5.3.4 Lesson"
        assert assignment.letter_grade == "A"
        assert assignment.points_earned == 5.0
        assert assignment.points_possible == 5.0
        assert assignment.percentage == 100.0
        assert assignment.is_missing is False

    def test_missing_assignment_flags(self) -> None:
        """Test that a missing assignment has correct flag values."""
        assignment = Assignment(
            date="2026-01-21",
            name="6.1.1 RP",
            letter_grade="F",
            points_earned=0.0,
            points_possible=10.0,
            percentage=0.0,
            is_missing=True,
            is_exempt=False,
            is_not_included=False,
            is_not_yet_graded=False,
        )
        assert assignment.is_missing is True
        assert assignment.is_exempt is False
        assert assignment.is_not_included is False

    def test_exempt_assignment_not_missing(self) -> None:
        """Test that exempt assignments are not marked as missing."""
        assignment = Assignment(
            date="2026-01-15",
            name="Quiz 3",
            letter_grade="F",
            points_earned=0.0,
            points_possible=10.0,
            percentage=0.0,
            is_missing=False,
            is_exempt=True,
            is_not_included=False,
            is_not_yet_graded=False,
        )
        assert assignment.is_exempt is True
        assert assignment.is_missing is False

    def test_not_yet_graded_assignment(self) -> None:
        """Test that not-yet-graded assignments are flagged correctly."""
        assignment = Assignment(
            date="2026-01-20",
            name="Chapter 6 Test",
            letter_grade="*",
            points_earned=0.0,
            points_possible=9.0,
            percentage=0.0,
            is_missing=False,
            is_exempt=False,
            is_not_included=False,
            is_not_yet_graded=True,
        )
        assert assignment.is_not_yet_graded is True
        assert assignment.is_missing is False


class TestCourse:
    """Tests for the Course dataclass."""

    def test_create_course_with_assignments(self) -> None:
        """Test creating a Course with a list of assignments."""
        assignment = Assignment(
            date="2026-01-12",
            name="5.3.4 Lesson",
            letter_grade="A",
            points_earned=5.0,
            points_possible=5.0,
            percentage=100.0,
            is_missing=False,
            is_exempt=False,
            is_not_included=False,
            is_not_yet_graded=False,
        )
        course = Course(
            name="Math 6",
            period="P1(A)",
            instructor="Motch, Michaela",
            overall_grade="D",
            assignments=[assignment],
        )
        assert course.name == "Math 6"
        assert course.period == "P1(A)"
        assert course.instructor == "Motch, Michaela"
        assert course.overall_grade == "D"
        assert len(course.assignments) == 1

    def test_course_default_empty_assignments(self) -> None:
        """Test that Course defaults to an empty assignment list."""
        course = Course(
            name="Science 6",
            period="P2(A)",
            instructor="Smith, John",
            overall_grade="B",
        )
        assert course.assignments == []


class TestGradeReport:
    """Tests for the GradeReport dataclass."""

    def test_create_grade_report(self) -> None:
        """Test creating a GradeReport with courses."""
        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student="Layla H.",
            grading_period="Q3",
            courses=[
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                ),
            ],
        )
        assert report.student == "Layla H."
        assert report.grading_period == "Q3"
        assert len(report.courses) == 1

    def test_grade_report_default_empty_courses(self) -> None:
        """Test that GradeReport defaults to an empty course list."""
        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student="Layla H.",
            grading_period="Q3",
        )
        assert report.courses == []


class TestAlertState:
    """Tests for the AlertState dataclass."""

    def test_create_alert_state_with_defaults(self) -> None:
        """Test creating AlertState with default empty values."""
        state = AlertState()
        assert state.alerted_missing == []
        assert state.last_run is None

    def test_create_alert_state_with_data(self) -> None:
        """Test creating AlertState with existing alert data."""
        state = AlertState(
            alerted_missing=[
                "Math 6::6.1.1 RP::2026-01-21",
                "Soc Sci 6::Brainpop: Mummies! Quiz::2026-01-26",
            ],
            last_run="2026-02-11T08:00:00Z",
        )
        assert len(state.alerted_missing) == 2
        assert state.last_run == "2026-02-11T08:00:00Z"


class TestAssignmentKey:
    """Tests for the assignment_key helper function."""

    def test_assignment_key_format(self) -> None:
        """Test that assignment_key produces correct format."""
        key = assignment_key("Math 6", "6.1.1 RP", "2026-01-21")
        assert key == "Math 6::6.1.1 RP::2026-01-21"

    def test_assignment_key_with_special_characters(self) -> None:
        """Test assignment_key with special characters in name."""
        key = assignment_key(
            "Soc Sci 6",
            "Brainpop: Mummies! Quiz",
            "2026-01-26",
        )
        assert key == "Soc Sci 6::Brainpop: Mummies! Quiz::2026-01-26"


class TestSerialization:
    """Tests for JSON serialization/deserialization of models."""

    def test_grade_report_to_dict(self) -> None:
        """Test converting a GradeReport to a dictionary."""
        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student="Layla H.",
            grading_period="Q3",
            courses=[
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        Assignment(
                            date="2026-01-12",
                            name="5.3.4 Lesson",
                            letter_grade="A",
                            points_earned=5.0,
                            points_possible=5.0,
                            percentage=100.0,
                            is_missing=False,
                            is_exempt=False,
                            is_not_included=False,
                            is_not_yet_graded=False,
                        ),
                    ],
                ),
            ],
        )
        data = report.to_dict()
        assert data["student"] == "Layla H."
        assert data["courses"][0]["name"] == "Math 6"
        assert data["courses"][0]["assignments"][0]["name"] == "5.3.4 Lesson"

    def test_grade_report_to_json_roundtrip(self) -> None:
        """Test that GradeReport survives JSON serialization roundtrip."""
        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student="Layla H.",
            grading_period="Q3",
            courses=[
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        Assignment(
                            date="2026-01-12",
                            name="5.3.4 Lesson",
                            letter_grade="A",
                            points_earned=5.0,
                            points_possible=5.0,
                            percentage=100.0,
                            is_missing=False,
                            is_exempt=False,
                            is_not_included=False,
                            is_not_yet_graded=False,
                        ),
                    ],
                ),
            ],
        )
        json_str = json.dumps(report.to_dict())
        loaded = json.loads(json_str)
        restored = GradeReport.from_dict(loaded)
        assert restored.student == report.student
        assert restored.courses[0].name == report.courses[0].name
        assert (
            restored.courses[0].assignments[0].name
            == report.courses[0].assignments[0].name
        )

    def test_alert_state_to_dict(self) -> None:
        """Test converting AlertState to a dictionary."""
        state = AlertState(
            alerted_missing=["Math 6::6.1.1 RP::2026-01-21"],
            last_run="2026-02-11T08:00:00Z",
        )
        data = state.to_dict()
        assert data["alerted_missing"] == ["Math 6::6.1.1 RP::2026-01-21"]
        assert data["last_run"] == "2026-02-11T08:00:00Z"

    def test_alert_state_from_dict(self) -> None:
        """Test creating AlertState from a dictionary."""
        data = {
            "alerted_missing": ["Math 6::6.1.1 RP::2026-01-21"],
            "last_run": "2026-02-11T08:00:00Z",
        }
        state = AlertState.from_dict(data)
        assert state.alerted_missing == ["Math 6::6.1.1 RP::2026-01-21"]
        assert state.last_run == "2026-02-11T08:00:00Z"

    def test_alert_state_from_empty_dict(self) -> None:
        """Test creating AlertState from empty/missing fields."""
        state = AlertState.from_dict({})
        assert state.alerted_missing == []
        assert state.last_run is None
