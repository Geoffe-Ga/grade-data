"""Tests for grade_data.alerter module."""

import json
from pathlib import Path
from unittest.mock import patch

import requests

from grade_data.alerter import (
    _post_webhook,
    build_missing_embed,
    build_resolved_embed,
    find_missing_assignments,
    find_new_missing,
    find_resolved_missing,
    load_alert_state,
    save_alert_state,
    send_alerts,
)
from grade_data.models import (
    AlertState,
    Assignment,
    Course,
    GradeReport,
)


def _make_assignment(
    name: str,
    *,
    is_missing: bool = False,
    date: str = "2026-01-21",
    points_possible: float = 10.0,
) -> Assignment:
    """Create a test assignment with sensible defaults."""
    return Assignment(
        date=date,
        name=name,
        letter_grade="F" if is_missing else "A",
        points_earned=0.0 if is_missing else 10.0,
        points_possible=points_possible,
        percentage=0.0 if is_missing else 100.0,
        is_missing=is_missing,
        is_exempt=False,
        is_not_included=False,
        is_not_yet_graded=False,
    )


def _make_report(courses: list[Course]) -> GradeReport:
    """Create a test GradeReport with given courses."""
    return GradeReport(
        last_updated="2026-02-11T08:00:00Z",
        student="Layla H.",
        grading_period="Q3",
        courses=courses,
    )


class TestFindMissingAssignments:
    """Tests for finding all missing assignments in a report."""

    def test_no_missing(self) -> None:
        """Test report with no missing assignments."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="A",
                    assignments=[_make_assignment("Lesson 1")],
                ),
            ]
        )
        missing = find_missing_assignments(report)
        assert missing == []

    def test_finds_missing(self) -> None:
        """Test that missing assignments are identified."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("Lesson 1"),
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        missing = find_missing_assignments(report)
        assert len(missing) == 1
        assert missing[0] == "Math 6::6.1.1 RP::2026-01-21"

    def test_finds_missing_across_courses(self) -> None:
        """Test finding missing assignments across multiple courses."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
                Course(
                    name="Soc Sci 6",
                    period="P3(A)",
                    instructor="Jones, Sarah",
                    overall_grade="F",
                    assignments=[
                        _make_assignment(
                            "Brainpop Quiz",
                            is_missing=True,
                            date="2026-01-26",
                        ),
                    ],
                ),
            ]
        )
        missing = find_missing_assignments(report)
        assert len(missing) == 2


class TestFindNewMissing:
    """Tests for identifying newly missing assignments."""

    def test_all_new_when_no_prior_state(self) -> None:
        """Test that all missing are new when state is empty."""
        current = ["Math 6::6.1.1 RP::2026-01-21"]
        state = AlertState()
        new = find_new_missing(current, state)
        assert new == ["Math 6::6.1.1 RP::2026-01-21"]

    def test_none_new_when_all_alerted(self) -> None:
        """Test that no new missing when all were already alerted."""
        current = ["Math 6::6.1.1 RP::2026-01-21"]
        state = AlertState(alerted_missing=["Math 6::6.1.1 RP::2026-01-21"])
        new = find_new_missing(current, state)
        assert new == []

    def test_identifies_only_new(self) -> None:
        """Test that only newly missing assignments are returned."""
        current = [
            "Math 6::6.1.1 RP::2026-01-21",
            "Math 6::6.2.1 RP::2026-01-27",
        ]
        state = AlertState(alerted_missing=["Math 6::6.1.1 RP::2026-01-21"])
        new = find_new_missing(current, state)
        assert new == ["Math 6::6.2.1 RP::2026-01-27"]


class TestFindResolvedMissing:
    """Tests for identifying resolved (turned-in) assignments."""

    def test_no_resolved_when_all_still_missing(self) -> None:
        """Test no resolved when all previously alerted are still missing."""
        current = ["Math 6::6.1.1 RP::2026-01-21"]
        state = AlertState(alerted_missing=["Math 6::6.1.1 RP::2026-01-21"])
        resolved = find_resolved_missing(current, state)
        assert resolved == []

    def test_finds_resolved(self) -> None:
        """Test that resolved assignments are identified."""
        current: list[str] = []
        state = AlertState(alerted_missing=["Math 6::6.1.1 RP::2026-01-21"])
        resolved = find_resolved_missing(current, state)
        assert resolved == ["Math 6::6.1.1 RP::2026-01-21"]

    def test_partial_resolution(self) -> None:
        """Test when only some previously missing are resolved."""
        current = ["Math 6::6.1.1 RP::2026-01-21"]
        state = AlertState(
            alerted_missing=[
                "Math 6::6.1.1 RP::2026-01-21",
                "Math 6::6.2.1 RP::2026-01-27",
            ],
        )
        resolved = find_resolved_missing(current, state)
        assert resolved == ["Math 6::6.2.1 RP::2026-01-27"]


class TestBuildMissingEmbed:
    """Tests for Discord embed payload building."""

    def test_embed_has_red_color(self) -> None:
        """Test that missing alert embed uses red color."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        new_keys = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_missing_embed(report, new_keys, [], "http://dash")
        assert embed["embeds"][0]["color"] == 0xFF0000

    def test_embed_title_contains_student_name(self) -> None:
        """Test that embed title includes student name."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        new_keys = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_missing_embed(report, new_keys, [], "http://dash")
        assert "Layla" in embed["embeds"][0]["title"]

    def test_embed_lists_new_missing_grouped_by_course(self) -> None:
        """Test that embed description groups new missing by course."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                        _make_assignment(
                            "6.2.1 RP",
                            is_missing=True,
                            date="2026-01-27",
                        ),
                    ],
                ),
            ]
        )
        new_keys = [
            "Math 6::6.1.1 RP::2026-01-21",
            "Math 6::6.2.1 RP::2026-01-27",
        ]
        embed = build_missing_embed(report, new_keys, [], "http://dash")
        desc = embed["embeds"][0]["description"]
        assert "**Math 6**" in desc
        assert "6.1.1 RP" in desc
        assert "6.2.1 RP" in desc

    def test_embed_shows_outstanding_count(self) -> None:
        """Test that embed shows count of other outstanding missing."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment(
                            "6.2.1 RP",
                            is_missing=True,
                            date="2026-01-27",
                        ),
                    ],
                ),
            ]
        )
        new_keys = ["Math 6::6.2.1 RP::2026-01-27"]
        still_outstanding = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_missing_embed(report, new_keys, still_outstanding, "http://dash")
        desc = embed["embeds"][0]["description"]
        assert "1 other missing" in desc
        assert "http://dash" in desc

    def test_embed_no_outstanding_line_when_zero(self) -> None:
        """Test that outstanding line is omitted when count is zero."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        new_keys = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_missing_embed(report, new_keys, [], "http://dash")
        desc = embed["embeds"][0]["description"]
        assert "other missing" not in desc

    def test_embed_includes_dashboard_link(self) -> None:
        """Test that embed always includes dashboard link when URL provided."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        new_keys = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_missing_embed(report, new_keys, [], "http://dash")
        desc = embed["embeds"][0]["description"]
        assert "[View Dashboard](http://dash)" in desc

    def test_embed_no_dashboard_link_when_url_empty(self) -> None:
        """Test that embed omits dashboard link when URL is empty."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        new_keys = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_missing_embed(report, new_keys, [], "")
        desc = embed["embeds"][0]["description"]
        assert "View Dashboard" not in desc

    def test_embed_uses_first_name_only(self) -> None:
        """Test that embed title uses first name without last initial."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        new_keys = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_missing_embed(report, new_keys, [], "http://dash")
        title = embed["embeds"][0]["title"]
        assert "Layla" in title
        assert "H." not in title


class TestBuildResolvedEmbed:
    """Tests for the resolved/completed embed."""

    def test_resolved_embed_has_green_color(self) -> None:
        """Test that resolved embed uses green color."""
        resolved = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_resolved_embed("Layla", resolved)
        assert embed["embeds"][0]["color"] == 0x00FF00

    def test_resolved_embed_lists_completed(self) -> None:
        """Test that resolved embed lists completed assignments."""
        resolved = ["Math 6::6.1.1 RP::2026-01-21"]
        embed = build_resolved_embed("Layla", resolved)
        desc = embed["embeds"][0]["description"]
        assert "6.1.1 RP" in desc
        assert "Math 6" in desc


class TestSendAlerts:
    """Tests for the send_alerts orchestration function."""

    @patch("grade_data.alerter._post_webhook")
    def test_sends_webhook_for_new_missing(self, mock_post) -> None:
        """Test that a webhook is sent when new missing assignments exist."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        state = AlertState()
        send_alerts(report, state, "http://webhook", "http://dash")
        mock_post.assert_called_once()

    @patch("grade_data.alerter._post_webhook")
    def test_no_webhook_when_no_new_missing(self, mock_post) -> None:
        """Test that no webhook is sent when all missing already alerted."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        state = AlertState(
            alerted_missing=["Math 6::6.1.1 RP::2026-01-21"],
        )
        send_alerts(report, state, "http://webhook", "http://dash")
        mock_post.assert_not_called()

    @patch("grade_data.alerter._post_webhook")
    def test_sends_resolved_webhook(self, mock_post) -> None:
        """Test that a resolved webhook is sent when assignments completed."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="A",
                    assignments=[_make_assignment("6.1.1 RP")],
                ),
            ]
        )
        state = AlertState(
            alerted_missing=["Math 6::6.1.1 RP::2026-01-21"],
        )
        send_alerts(report, state, "http://webhook", "http://dash")
        mock_post.assert_called_once()
        payload = mock_post.call_args[0][1]
        assert payload["embeds"][0]["color"] == 0x00FF00

    @patch("grade_data.alerter._post_webhook")
    def test_returns_updated_state_with_new_missing(self, mock_post) -> None:
        """Test that send_alerts returns state updated with new alerts."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="D",
                    assignments=[
                        _make_assignment("6.1.1 RP", is_missing=True),
                    ],
                ),
            ]
        )
        state = AlertState()
        updated = send_alerts(report, state, "http://webhook", "http://dash")
        assert "Math 6::6.1.1 RP::2026-01-21" in updated.alerted_missing

    @patch("grade_data.alerter._post_webhook")
    def test_removes_resolved_from_state(self, mock_post) -> None:
        """Test that resolved assignments are removed from state."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="A",
                    assignments=[_make_assignment("6.1.1 RP")],
                ),
            ]
        )
        state = AlertState(
            alerted_missing=["Math 6::6.1.1 RP::2026-01-21"],
        )
        updated = send_alerts(report, state, "http://webhook", "http://dash")
        assert "Math 6::6.1.1 RP::2026-01-21" not in updated.alerted_missing

    @patch("grade_data.alerter._post_webhook")
    def test_no_change_when_no_missing(self, mock_post) -> None:
        """Test that state is unchanged when nothing is missing."""
        report = _make_report(
            [
                Course(
                    name="Math 6",
                    period="P1(A)",
                    instructor="Motch, Michaela",
                    overall_grade="A",
                    assignments=[_make_assignment("Lesson 1")],
                ),
            ]
        )
        state = AlertState()
        updated = send_alerts(report, state, "http://webhook", "http://dash")
        assert updated.alerted_missing == []

    @patch("grade_data.alerter._post_webhook")
    def test_state_has_updated_last_run(self, mock_post) -> None:
        """Test that last_run is updated after send_alerts."""
        report = _make_report([])
        state = AlertState()
        updated = send_alerts(report, state, "http://webhook", "http://dash")
        assert updated.last_run is not None


class TestAlertStatePersistence:
    """Tests for loading and saving alert state."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Test that AlertState survives save/load roundtrip."""
        state = AlertState(
            alerted_missing=["Math 6::6.1.1 RP::2026-01-21"],
            last_run="2026-02-11T08:00:00Z",
        )
        path = tmp_path / "state.json"
        save_alert_state(state, str(path))
        loaded = load_alert_state(str(path))
        assert loaded.alerted_missing == state.alerted_missing
        assert loaded.last_run == state.last_run

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Test that loading a missing file returns empty state."""
        path = tmp_path / "nonexistent.json"
        loaded = load_alert_state(str(path))
        assert loaded.alerted_missing == []
        assert loaded.last_run is None

    def test_save_creates_valid_json(self, tmp_path: Path) -> None:
        """Test that saved state is valid JSON."""
        state = AlertState(
            alerted_missing=["Math 6::6.1.1 RP::2026-01-21"],
            last_run="2026-02-11T08:00:00Z",
        )
        path = tmp_path / "state.json"
        save_alert_state(state, str(path))
        data = json.loads(path.read_text())
        assert "alerted_missing" in data
        assert "last_run" in data


class TestPostWebhook:
    """Tests for the _post_webhook helper."""

    @patch("grade_data.alerter.requests.post")
    def test_posts_json_payload(self, mock_post) -> None:
        """Test that _post_webhook sends JSON payload to the URL."""
        payload = {"embeds": [{"title": "Test"}]}
        _post_webhook("http://webhook", payload)
        mock_post.assert_called_once_with("http://webhook", json=payload, timeout=10)

    @patch("grade_data.alerter.requests.post")
    def test_logs_and_swallows_request_exception(self, mock_post) -> None:
        """Test that RequestException is caught and logged, not raised."""
        mock_post.side_effect = requests.exceptions.ConnectionError("fail")
        # Should not raise
        _post_webhook("http://webhook", {"embeds": []})
