"""Tests for grade_data.parser module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grade_data.models import GradeReport
from grade_data.parser import (
    _parse_score,
    fetch_and_parse,
    fetch_emails,
    parse_email_body,
    save_grade_report,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture()
def sample_email_text() -> str:
    """Load the sample email fixture."""
    return (FIXTURES_DIR / "sample_email.txt").read_text()


# ---------------------------------------------------------------------------
# parse_email_body — pure text parsing (no I/O)
# ---------------------------------------------------------------------------


class TestParseEmailBodyHeader:
    """Tests for header field parsing from email body text."""

    def test_parses_student_name(self, sample_email_text) -> None:
        """Test parsing of the Student header field."""
        course = parse_email_body(sample_email_text)
        assert course.student == "Layla H."

    def test_parses_grading_period(self, sample_email_text) -> None:
        """Test parsing of the Grading period header field."""
        course = parse_email_body(sample_email_text)
        assert course.grading_period == "Q3"

    def test_parses_course_name(self, sample_email_text) -> None:
        """Test parsing of the Course header field."""
        course = parse_email_body(sample_email_text)
        assert course.course.name == "Math 6"

    def test_parses_period(self, sample_email_text) -> None:
        """Test parsing of the Period header field."""
        course = parse_email_body(sample_email_text)
        assert course.course.period == "P1(A)"

    def test_parses_instructor(self, sample_email_text) -> None:
        """Test parsing of the Instructor header field."""
        course = parse_email_body(sample_email_text)
        assert course.course.instructor == "Motch, Michaela"

    def test_parses_overall_grade(self, sample_email_text) -> None:
        """Test parsing of the overall grade (handles ** literal)."""
        course = parse_email_body(sample_email_text)
        assert course.course.overall_grade == "D"


class TestParseEmailBodyAssignments:
    """Tests for assignment line parsing."""

    def test_parses_correct_number_of_assignments(self, sample_email_text) -> None:
        """Test that all assignment lines are parsed."""
        course = parse_email_body(sample_email_text)
        assert len(course.course.assignments) == 10

    def test_parses_normal_assignment(self, sample_email_text) -> None:
        """Test parsing a normal graded assignment."""
        course = parse_email_body(sample_email_text)
        a = course.course.assignments[0]
        assert a.date == "2026-01-12"
        assert a.name == "5.3.4 Lesson"
        assert a.letter_grade == "A"
        assert a.points_earned == 5.0
        assert a.points_possible == 5.0
        assert a.percentage == 100.0
        assert a.is_missing is False
        assert a.is_exempt is False
        assert a.is_not_included is False
        assert a.is_not_yet_graded is False

    def test_parses_fractional_score(self, sample_email_text) -> None:
        """Test parsing a score with decimal percentage (66.67%)."""
        course = parse_email_body(sample_email_text)
        a = course.course.assignments[2]
        assert a.name == "Ch 5 Check #3"
        assert a.points_earned == 6.0
        assert a.points_possible == 9.0
        assert a.percentage == pytest.approx(66.67)


class TestParseEmailBodyMissing:
    """Tests for missing assignment detection."""

    def test_zero_score_is_missing(self, sample_email_text) -> None:
        """Test that 0/N with no flag is marked as missing."""
        course = parse_email_body(sample_email_text)
        rp = next(a for a in course.course.assignments if a.name == "6.1.1 RP")
        assert rp.is_missing is True
        assert rp.points_earned == 0.0
        assert rp.points_possible == 10.0

    def test_second_missing_assignment(self, sample_email_text) -> None:
        """Test a second missing assignment is also detected."""
        course = parse_email_body(sample_email_text)
        rp = next(a for a in course.course.assignments if a.name == "6.1.2 RP")
        assert rp.is_missing is True


class TestParseEmailBodyExempt:
    """Tests for exempt (^) assignment handling."""

    def test_exempt_zero_not_missing(self, sample_email_text) -> None:
        """Test that ^ (exempt) assignment with 0 score is NOT missing."""
        course = parse_email_body(sample_email_text)
        quiz = next(a for a in course.course.assignments if a.name == "Quiz 4")
        assert quiz.is_exempt is True
        assert quiz.is_missing is False
        assert quiz.points_earned == 0.0

    def test_exempt_flag_stripped_from_name(self, sample_email_text) -> None:
        """Test that the ^ prefix is stripped from the assignment name."""
        course = parse_email_body(sample_email_text)
        quiz = next(a for a in course.course.assignments if a.name == "Quiz 4")
        assert not quiz.name.startswith("^")


class TestParseEmailBodyNotIncluded:
    """Tests for not-included (*) assignment handling."""

    def test_not_included_zero_not_missing(self, sample_email_text) -> None:
        """Test that * (not included) assignment with 0 score is NOT missing."""
        course = parse_email_body(sample_email_text)
        notes = next(
            a for a in course.course.assignments if a.name == "Participation Notes"
        )
        assert notes.is_not_included is True
        assert notes.is_missing is False

    def test_not_included_flag_stripped_from_name(self, sample_email_text) -> None:
        """Test that the * prefix is stripped from the assignment name."""
        course = parse_email_body(sample_email_text)
        notes = next(
            a for a in course.course.assignments if a.name == "Participation Notes"
        )
        assert not notes.name.startswith("*")


class TestParseEmailBodyNotYetGraded:
    """Tests for not-yet-graded (Grade: * (-/N)) handling."""

    def test_not_yet_graded_detected(self, sample_email_text) -> None:
        """Test that Grade: * (-/9) is flagged as not yet graded."""
        course = parse_email_body(sample_email_text)
        hw = next(a for a in course.course.assignments if a.name == "Homework 7")
        assert hw.is_not_yet_graded is True
        assert hw.is_missing is False
        assert hw.letter_grade == "*"

    def test_not_yet_graded_score_values(self, sample_email_text) -> None:
        """Test score values for not-yet-graded assignment."""
        course = parse_email_body(sample_email_text)
        hw = next(a for a in course.course.assignments if a.name == "Homework 7")
        assert hw.points_earned == 0.0
        assert hw.points_possible == 9.0
        assert hw.percentage == 0.0


class TestParseEmailBodyEdgeCases:
    """Tests for edge cases in parsing."""

    def test_score_over_100_percent(self, sample_email_text) -> None:
        """Test parsing score exceeding 100% (extra credit)."""
        course = parse_email_body(sample_email_text)
        ec = next(
            a
            for a in course.course.assignments
            if a.name == "Extra Credit: Bonus (Part 2)"
        )
        assert ec.points_earned == pytest.approx(10.74)
        assert ec.points_possible == 10.0
        assert ec.percentage == pytest.approx(107.4)

    def test_special_characters_in_name(self, sample_email_text) -> None:
        """Test parsing assignment name with colons, parens, periods."""
        course = parse_email_body(sample_email_text)
        review = next(a for a in course.course.assignments if "Review" in a.name)
        assert review.name == "Ch. 5: Review (Part 2)"

    def test_date_format_conversion(self, sample_email_text) -> None:
        """Test that dates are converted from MM/DD/YYYY to ISO format."""
        course = parse_email_body(sample_email_text)
        a = course.course.assignments[0]
        assert a.date == "2026-01-12"

    def test_missing_header_returns_empty(self) -> None:
        """Test that a missing header field returns empty string."""
        body = "Some random text\nwith no headers\n"
        result = parse_email_body(body)
        assert result.student == ""
        assert result.course.name == ""

    def test_missing_overall_grade_returns_empty(self) -> None:
        """Test that missing overall grade line returns empty string."""
        body = "Course        :  Math 6\nNo grade line here\n"
        result = parse_email_body(body)
        assert result.course.overall_grade == ""


# ---------------------------------------------------------------------------
# fetch_emails — IMAP I/O (mocked)
# ---------------------------------------------------------------------------


class TestFetchEmails:
    """Tests for IMAP email fetching with mocked connections."""

    def _build_mock_imap(self, raw_bodies: list[bytes]) -> MagicMock:
        """Build a mock IMAP4_SSL instance returning given email bodies."""
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"1"])

        # search returns message UIDs
        uids = b" ".join(str(i + 1).encode() for i in range(len(raw_bodies)))
        mock_conn.search.return_value = ("OK", [uids])

        # fetch returns one message per UID
        def fake_fetch(uid: bytes, parts: str) -> tuple[str, list[tuple]]:
            idx = int(uid) - 1
            return (
                "OK",
                [(b"1 (RFC822 {%d})" % len(raw_bodies[idx]), raw_bodies[idx])],
            )

        mock_conn.fetch.side_effect = fake_fetch
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        return mock_conn

    def _make_raw_email(self, body_text: str) -> bytes:
        """Build a minimal RFC822 email from plain text body."""
        return (
            "From: pwsupport@unionsd.org\r\n"
            "Subject: Progress report for Layla H.\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n" + body_text
        ).encode("utf-8")

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_fetch_returns_grade_report(
        self, mock_imap_class, sample_email_text
    ) -> None:
        """Test that fetch_emails returns a GradeReport."""
        raw = self._make_raw_email(sample_email_text)
        mock_imap_class.return_value = self._build_mock_imap([raw])

        report = fetch_emails("fake@example.invalid", "fake-pass")

        assert isinstance(report, GradeReport)
        assert report.student == "Layla H."
        assert len(report.courses) == 1
        assert report.courses[0].name == "Math 6"

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_fetch_deduplicates_by_course(
        self, mock_imap_class, sample_email_text
    ) -> None:
        """Test that duplicate emails for the same course keep only the latest."""
        raw = self._make_raw_email(sample_email_text)
        mock_imap_class.return_value = self._build_mock_imap([raw, raw])

        report = fetch_emails("fake@example.invalid", "fake-pass")

        assert len(report.courses) == 1

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_fetch_no_emails_returns_empty_report(self, mock_imap_class) -> None:
        """Test that no matching emails returns a report with no courses."""
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"0"])
        mock_conn.search.return_value = ("OK", [b""])
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_imap_class.return_value = mock_conn

        report = fetch_emails("fake@example.invalid", "fake-pass")

        assert report.courses == []

    def _make_multipart_email(self, body_text: str) -> bytes:
        """Build an RFC822 multipart email with text/plain body."""
        boundary = "boundary123"
        return (
            "From: pwsupport@unionsd.org\r\n"
            "Subject: Progress report for Layla H.\r\n"
            f"Content-Type: multipart/mixed; boundary={boundary}\r\n"
            "\r\n"
            f"--{boundary}\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "\r\n"
            "<html><body>ignored</body></html>\r\n"
            f"--{boundary}\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n" + body_text + "\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_fetch_handles_multipart_email(
        self, mock_imap_class, sample_email_text
    ) -> None:
        """Test that multipart emails extract the text/plain part."""
        raw = self._make_multipart_email(sample_email_text)
        mock_imap_class.return_value = self._build_mock_imap([raw])

        report = fetch_emails("fake@example.invalid", "fake-pass")

        assert len(report.courses) == 1
        assert report.courses[0].name == "Math 6"

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_fetch_skips_empty_body_email(self, mock_imap_class) -> None:
        """Test that emails with no text body are skipped."""
        raw = (
            b"From: pwsupport@unionsd.org\r\n"
            b"Subject: Empty\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n"
            b"\r\n"
            b"<html></html>"
        )
        mock_imap_class.return_value = self._build_mock_imap([raw])

        report = fetch_emails("fake@example.invalid", "fake-pass")

        assert report.courses == []


# ---------------------------------------------------------------------------
# fetch_and_parse — full pipeline (delegates to fetch_emails)
# ---------------------------------------------------------------------------


class TestFetchAndParse:
    """Tests for the fetch_and_parse orchestrator function."""

    @patch("grade_data.parser.fetch_emails")
    def test_returns_grade_report(self, mock_fetch) -> None:
        """Test that fetch_and_parse returns a valid GradeReport."""
        mock_fetch.return_value = GradeReport(
            last_updated="2026-02-11T00:00:00Z",
            student="Layla H.",
            grading_period="Q3",
        )
        report = fetch_and_parse("fake@example.invalid", "fake-pass")
        assert isinstance(report, GradeReport)

    @patch("grade_data.parser.fetch_emails")
    def test_report_has_student_name(self, mock_fetch) -> None:
        """Test that the returned report contains a student name."""
        mock_fetch.return_value = GradeReport(
            last_updated="2026-02-11T00:00:00Z",
            student="Layla H.",
            grading_period="Q3",
        )
        report = fetch_and_parse("fake@example.invalid", "fake-pass")
        assert report.student == "Layla H."


# ---------------------------------------------------------------------------
# save_grade_report — file output
# ---------------------------------------------------------------------------


class TestSaveGradeReport:
    """Tests for the save_grade_report function."""

    def test_writes_json_file(self, tmp_path: Path) -> None:
        """Test that save_grade_report writes a valid JSON file."""
        report = GradeReport(
            last_updated="2026-02-11T00:00:00Z",
            student="Layla H.",
            grading_period="Q3",
        )
        output_path = tmp_path / "grades.json"

        save_grade_report(report, str(output_path))

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["student"] == "Layla H."

    def test_output_matches_schema(self, tmp_path: Path) -> None:
        """Test that the output JSON matches the expected schema."""
        report = GradeReport(
            last_updated="2026-02-11T00:00:00Z",
            student="Layla H.",
            grading_period="Q3",
        )
        output_path = tmp_path / "grades.json"

        save_grade_report(report, str(output_path))

        data = json.loads(output_path.read_text())
        assert "last_updated" in data
        assert "student" in data
        assert "grading_period" in data
        assert "courses" in data


# ---------------------------------------------------------------------------
# _parse_score — edge cases
# ---------------------------------------------------------------------------


class TestParseScoreEdgeCases:
    """Tests for _parse_score with malformed input."""

    def test_malformed_score_returns_zeros(self) -> None:
        """Test that a score string that doesn't match returns all zeros."""
        result = _parse_score("N/A")
        assert result == (0.0, 0.0, 0.0)

    def test_empty_string_returns_zeros(self) -> None:
        """Test that an empty score string returns all zeros."""
        result = _parse_score("")
        assert result == (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# fetch_emails — IMAP edge cases for non-standard responses
# ---------------------------------------------------------------------------


class TestFetchEmailsEdgeCases:
    """Tests for IMAP edge cases in fetch_emails."""

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_fetch_skips_non_tuple_msg_data(self, mock_imap_class) -> None:
        """Test that non-tuple entries in fetch response are skipped."""
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        # IMAP fetch returns a closing paren bytes as msg_data[0]
        mock_conn.fetch.return_value = ("OK", [b")"])
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_imap_class.return_value = mock_conn

        report = fetch_emails("fake@example.invalid", "fake-pass")

        assert report.courses == []

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_fetch_skips_non_bytes_raw_email(self, mock_imap_class) -> None:
        """Test that tuple entries with non-bytes payload are skipped."""
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        # Tuple but second element is not bytes
        mock_conn.fetch.return_value = ("OK", [(b"1 (RFC822 {0})", None)])
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_imap_class.return_value = mock_conn

        report = fetch_emails("fake@example.invalid", "fake-pass")

        assert report.courses == []

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_text_plain_non_bytes_payload_skipped(self, mock_imap_class) -> None:
        """Test that a text/plain message with non-bytes payload is skipped."""
        raw = (
            b"From: pwsupport@unionsd.org\r\n"
            b"Subject: Progress report for Layla H.\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"body text"
        )
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        mock_conn.fetch.return_value = (
            "OK",
            [(b"1 (RFC822 {%d})" % len(raw), raw)],
        )
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_imap_class.return_value = mock_conn

        # Patch the parsed message's get_payload to return a string (non-bytes)
        with patch("grade_data.parser.email.message_from_bytes") as mock_parse:
            mock_msg = MagicMock()
            mock_msg.is_multipart.return_value = False
            mock_msg.get_content_type.return_value = "text/plain"
            mock_msg.get_payload.return_value = "not bytes"
            mock_parse.return_value = mock_msg

            report = fetch_emails("fake@example.invalid", "fake-pass")

        assert report.courses == []

    @patch("grade_data.parser.imaplib.IMAP4_SSL")
    def test_multipart_no_text_plain_returns_empty(self, mock_imap_class) -> None:
        """Test that multipart email with no text/plain part is skipped."""
        boundary = "boundary456"
        raw = (
            "From: pwsupport@unionsd.org\r\n"
            "Subject: Progress report for Layla H.\r\n"
            f"Content-Type: multipart/mixed; boundary={boundary}\r\n"
            "\r\n"
            f"--{boundary}\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "\r\n"
            "<html><body>no plain text</body></html>\r\n"
            f"--{boundary}--\r\n"
        ).encode()
        mock_conn = MagicMock()
        mock_conn.login.return_value = ("OK", [b"Logged in"])
        mock_conn.select.return_value = ("OK", [b"1"])
        mock_conn.search.return_value = ("OK", [b"1"])
        mock_conn.fetch.return_value = (
            "OK",
            [(b"1 (RFC822 {%d})" % len(raw), raw)],
        )
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_imap_class.return_value = mock_conn

        report = fetch_emails("fake@example.invalid", "fake-pass")

        assert report.courses == []
