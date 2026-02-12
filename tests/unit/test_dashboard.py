"""Tests for grade_data.dashboard module."""

from pathlib import Path

from grade_data.dashboard import build_dashboard
from grade_data.models import Assignment, Course, GradeReport


def _make_assignment(
    name: str,
    *,
    is_missing: bool = False,
    is_exempt: bool = False,
    is_not_included: bool = False,
    is_not_yet_graded: bool = False,
    letter_grade: str = "A",
    points_earned: float = 10.0,
    points_possible: float = 10.0,
    percentage: float = 100.0,
    date: str = "2026-01-12",
) -> Assignment:
    """Create a test assignment with sensible defaults."""
    return Assignment(
        date=date,
        name=name,
        letter_grade=letter_grade,
        points_earned=points_earned,
        points_possible=points_possible,
        percentage=percentage,
        is_missing=is_missing,
        is_exempt=is_exempt,
        is_not_included=is_not_included,
        is_not_yet_graded=is_not_yet_graded,
    )


def _make_report() -> GradeReport:
    """Create a test GradeReport for dashboard tests."""
    return GradeReport(
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
                    _make_assignment("5.3.4 Lesson"),
                    _make_assignment(
                        "6.1.1 RP",
                        is_missing=True,
                        letter_grade="F",
                        points_earned=0.0,
                        percentage=0.0,
                        date="2026-01-21",
                    ),
                    _make_assignment(
                        "Quiz 4",
                        is_exempt=True,
                        letter_grade="F",
                        points_earned=0.0,
                        points_possible=9.0,
                        percentage=0.0,
                    ),
                    _make_assignment(
                        "Homework 7",
                        is_not_yet_graded=True,
                        letter_grade="*",
                        points_earned=0.0,
                        points_possible=9.0,
                        percentage=0.0,
                        date="2026-01-28",
                    ),
                ],
            ),
            Course(
                name="Soc Sci 6",
                period="P3(A)",
                instructor="Jones, Sarah",
                overall_grade="A",
                assignments=[
                    _make_assignment("Brainpop Quiz"),
                ],
            ),
        ],
    )


class TestBuildDashboardFileOutput:
    """Tests for file creation and directory handling."""

    def test_creates_output_file(self, tmp_path: Path) -> None:
        """Test that build_dashboard creates the output HTML file."""
        output = tmp_path / "docs" / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        assert output.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that build_dashboard creates parent directories."""
        output = tmp_path / "nested" / "docs" / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        assert output.exists()


class TestBuildDashboardHtmlStructure:
    """Tests for basic HTML document structure."""

    def test_output_is_html(self, tmp_path: Path) -> None:
        """Test that the output file contains HTML."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "</html>" in content

    def test_has_viewport_meta(self, tmp_path: Path) -> None:
        """Test that the HTML includes viewport meta for mobile."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "viewport" in content

    def test_has_title(self, tmp_path: Path) -> None:
        """Test that the page has a title."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "<title>" in content
        assert "Grade" in content


class TestBuildDashboardPasswordProtection:
    """Tests for client-side password protection."""

    def test_output_contains_password_hash(self, tmp_path: Path) -> None:
        """Test that the password hash is embedded in the HTML."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "abc123def456", str(output))
        content = output.read_text()
        assert "abc123def456" in content

    def test_has_password_input(self, tmp_path: Path) -> None:
        """Test that a password input element exists."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert 'type="password"' in content

    def test_uses_web_crypto_api(self, tmp_path: Path) -> None:
        """Test that Web Crypto API is used for hashing (not external lib)."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "crypto.subtle" in content

    def test_uses_session_storage(self, tmp_path: Path) -> None:
        """Test that sessionStorage is used for auth persistence."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "sessionStorage" in content


class TestBuildDashboardGradeData:
    """Tests for embedded grade data."""

    def test_grade_data_embedded(self, tmp_path: Path) -> None:
        """Test that grade data JSON is embedded in the HTML."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "GRADE_DATA" in content

    def test_student_name_in_output(self, tmp_path: Path) -> None:
        """Test that the student name appears in the output."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "Layla H." in content

    def test_course_names_in_output(self, tmp_path: Path) -> None:
        """Test that all course names appear in the output."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "Math 6" in content
        assert "Soc Sci 6" in content

    def test_last_updated_in_output(self, tmp_path: Path) -> None:
        """Test that last updated timestamp appears."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "2026-02-11" in content


class TestBuildDashboardMissingPanel:
    """Tests for the missing assignments panel."""

    def test_missing_assignment_highlighted(self, tmp_path: Path) -> None:
        """Test that missing assignments are identifiable in the output."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "6.1.1 RP" in content
        assert "Missing" in content or "missing" in content

    def test_not_yet_graded_identifiable(self, tmp_path: Path) -> None:
        """Test that not-yet-graded assignments are identifiable."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "Homework 7" in content

    def test_exempt_identifiable(self, tmp_path: Path) -> None:
        """Test that exempt assignments are identifiable."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "Quiz 4" in content


class TestBuildDashboardStyling:
    """Tests for CSS and visual styling."""

    def test_has_inline_css(self, tmp_path: Path) -> None:
        """Test that CSS is inline (self-contained)."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "<style>" in content

    def test_has_css_variables(self, tmp_path: Path) -> None:
        """Test that CSS variables are used for theming."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "--" in content

    def test_no_external_css_dependencies(self, tmp_path: Path) -> None:
        """Test that no external CSS CDNs are required."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert 'rel="stylesheet" href="http' not in content

    def test_has_inline_javascript(self, tmp_path: Path) -> None:
        """Test that JavaScript is inline (self-contained)."""
        output = tmp_path / "index.html"
        build_dashboard(_make_report(), "fakehash123", str(output))
        content = output.read_text()
        assert "<script>" in content


class TestBuildDashboardEdgeCases:
    """Tests for edge cases."""

    def test_empty_courses(self, tmp_path: Path) -> None:
        """Test dashboard with no courses."""
        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student="Layla H.",
            grading_period="Q3",
        )
        output = tmp_path / "index.html"
        build_dashboard(report, "fakehash123", str(output))
        content = output.read_text()
        assert "Layla H." in content
        assert "<html" in content

    def test_course_with_no_assignments(self, tmp_path: Path) -> None:
        """Test dashboard with a course that has no assignments."""
        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student="Layla H.",
            grading_period="Q3",
            courses=[
                Course(
                    name="Art 6",
                    period="P5(A)",
                    instructor="Smith, Jane",
                    overall_grade="A",
                    assignments=[],
                ),
            ],
        )
        output = tmp_path / "index.html"
        build_dashboard(report, "fakehash123", str(output))
        content = output.read_text()
        assert "Art 6" in content
