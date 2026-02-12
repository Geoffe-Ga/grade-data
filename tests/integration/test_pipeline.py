"""Integration tests for the full grade tracking pipeline.

Tests the end-to-end flow: parse email → grade report → alerter → dashboard.
All I/O is mocked; tests verify data flows correctly between components.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from grade_data.alerter import (
    find_missing_assignments,
    load_alert_state,
    save_alert_state,
    send_alerts,
)
from grade_data.dashboard import build_dashboard
from grade_data.models import AlertState, GradeReport
from grade_data.parser import parse_email_body, save_grade_report

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.integration
class TestParseToJson:
    """Test parsing email text and saving to JSON."""

    def test_parse_and_save_roundtrip(self, tmp_path: Path) -> None:
        """Test that parsed email saves to JSON and loads back correctly."""
        email_text = (FIXTURES_DIR / "sample_email.txt").read_text()
        parsed = parse_email_body(email_text)

        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student=parsed.student,
            grading_period=parsed.grading_period,
            courses=[parsed.course],
        )

        output_path = tmp_path / "grades.json"
        save_grade_report(report, str(output_path))

        loaded_data = json.loads(output_path.read_text())
        loaded_report = GradeReport.from_dict(loaded_data)

        assert loaded_report.student == "Layla H."
        assert loaded_report.grading_period == "Q3"
        assert len(loaded_report.courses) == 1
        assert loaded_report.courses[0].name == "Math 6"
        assert len(loaded_report.courses[0].assignments) == 10

    def test_parse_matches_expected_fixture(self) -> None:
        """Test that parsed output matches sample_grades.json fixture."""
        email_text = (FIXTURES_DIR / "sample_email.txt").read_text()
        expected = json.loads((FIXTURES_DIR / "sample_grades.json").read_text())
        parsed = parse_email_body(email_text)

        assert parsed.student == expected["student"]
        assert parsed.grading_period == expected["grading_period"]
        assert parsed.course.name == expected["courses"][0]["name"]
        assert len(parsed.course.assignments) == len(
            expected["courses"][0]["assignments"]
        )

        for actual, exp in zip(
            parsed.course.assignments,
            expected["courses"][0]["assignments"],
            strict=True,
        ):
            assert actual.name == exp["name"]
            assert actual.date == exp["date"]
            assert actual.is_missing == exp["is_missing"]
            assert actual.is_exempt == exp["is_exempt"]
            assert actual.is_not_included == exp["is_not_included"]
            assert actual.is_not_yet_graded == exp["is_not_yet_graded"]


@pytest.mark.integration
class TestParseToAlertPipeline:
    """Test the parse → alert flow."""

    @patch("grade_data.alerter._post_webhook")
    def test_parsed_report_triggers_alerts(self, mock_post) -> None:
        """Test that parsing an email and running alerts sends webhooks."""
        email_text = (FIXTURES_DIR / "sample_email.txt").read_text()
        parsed = parse_email_body(email_text)

        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student=parsed.student,
            grading_period=parsed.grading_period,
            courses=[parsed.course],
        )

        state = AlertState()
        updated = send_alerts(report, state, "http://webhook", "http://dash")

        # Sample email has 2 missing assignments
        assert len(find_missing_assignments(report)) == 2
        assert len(updated.alerted_missing) == 2
        mock_post.assert_called_once()

    @patch("grade_data.alerter._post_webhook")
    def test_second_run_no_new_alerts(self, mock_post) -> None:
        """Test that re-running with same data sends no new alerts."""
        email_text = (FIXTURES_DIR / "sample_email.txt").read_text()
        parsed = parse_email_body(email_text)

        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student=parsed.student,
            grading_period=parsed.grading_period,
            courses=[parsed.course],
        )

        # First run — alerts are sent
        state = AlertState()
        updated = send_alerts(report, state, "http://webhook", "http://dash")
        assert mock_post.call_count == 1

        # Second run — no new alerts
        mock_post.reset_mock()
        updated2 = send_alerts(report, updated, "http://webhook", "http://dash")
        mock_post.assert_not_called()
        assert updated2.alerted_missing == updated.alerted_missing


@pytest.mark.integration
class TestAlertStatePersistencePipeline:
    """Test alert state save/load across runs."""

    @patch("grade_data.alerter._post_webhook")
    def test_state_survives_save_load_cycle(self, mock_post, tmp_path: Path) -> None:
        """Test that alert state persists correctly between runs."""
        email_text = (FIXTURES_DIR / "sample_email.txt").read_text()
        parsed = parse_email_body(email_text)
        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student=parsed.student,
            grading_period=parsed.grading_period,
            courses=[parsed.course],
        )

        state_path = str(tmp_path / "state.json")

        # Run 1: initial alert
        state = load_alert_state(state_path)
        updated = send_alerts(report, state, "http://webhook", "http://dash")
        save_alert_state(updated, state_path)

        # Run 2: reload state, no new alerts
        mock_post.reset_mock()
        reloaded = load_alert_state(state_path)
        assert reloaded.alerted_missing == updated.alerted_missing

        updated2 = send_alerts(report, reloaded, "http://webhook", "http://dash")
        mock_post.assert_not_called()
        assert updated2.alerted_missing == updated.alerted_missing


@pytest.mark.integration
class TestParseToDashboardPipeline:
    """Test the parse → dashboard flow."""

    def test_parsed_report_builds_dashboard(self, tmp_path: Path) -> None:
        """Test that a parsed report produces a valid dashboard."""
        email_text = (FIXTURES_DIR / "sample_email.txt").read_text()
        parsed = parse_email_body(email_text)
        report = GradeReport(
            last_updated="2026-02-11T08:00:00Z",
            student=parsed.student,
            grading_period=parsed.grading_period,
            courses=[parsed.course],
        )

        output = tmp_path / "docs" / "index.html"
        build_dashboard(report, "fakehash", str(output))

        content = output.read_text()
        assert "Layla H." in content
        assert "Math 6" in content
        assert "6.1.1 RP" in content
        assert "GRADE_DATA" in content
