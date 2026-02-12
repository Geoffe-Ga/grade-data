"""Email fetching and grade parsing.

Connects to Gmail via IMAP, fetches PowerSchool grade report emails,
and parses them into a structured GradeReport.
"""

from __future__ import annotations

import email
import imaplib
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from grade_data.models import Assignment, Course, GradeReport

if TYPE_CHECKING:
    from email.message import Message

logger = logging.getLogger(__name__)

# Regex for assignment lines:
#   01/12/2026  5.3.4 Lesson                           Grade: A  (5/5 = 100%)
_ASSIGNMENT_RE = re.compile(
    r"^\s+(\d{2}/\d{2}/\d{4})\s+(.+?)\s{2,}Grade:\s+(\S+)\s+\((.+?)\)$",
    re.MULTILINE,
)

# Regex for not-yet-graded lines:
#   01/28/2026  Homework 7                             Grade: *   (-/9)
_NOT_YET_GRADED_RE = re.compile(
    r"^\s+(\d{2}/\d{2}/\d{4})\s+(.+?)\s{2,}Grade:\s+\*\s+\(-/(\d+(?:\.\d+)?)\)$",
    re.MULTILINE,
)

_SENDER = "pwsupport@unionsd.org"
_IMAP_HOST = "imap.gmail.com"
_GMAIL_ALL_MAIL = '"[Gmail]/All Mail"'


@dataclass
class ParsedEmail:
    """Intermediate result from parsing a single email body."""

    student: str
    grading_period: str
    course: Course


def _parse_header(body: str, field: str) -> str:
    """Extract a header field value from the email body.

    Args:
        body: The full email body text.
        field: The field label (e.g. ``"Course"``).

    Returns:
        The stripped field value.
    """
    pattern = re.compile(rf"^{re.escape(field)}\s*:\s*(.+)$", re.MULTILINE)
    match = pattern.search(body)
    if match:
        return match.group(1).strip()
    return ""


def _parse_overall_grade(body: str) -> str:
    """Extract the overall grade from the email body.

    Handles the literal ``**`` in ``Current overall grade**:``.

    Args:
        body: The full email body text.

    Returns:
        The letter grade string.
    """
    pattern = re.compile(r"^Current overall grade\*\*:\s+(\S+)", re.MULTILINE)
    match = pattern.search(body)
    if match:
        return match.group(1).strip()
    return ""


def _convert_date(date_str: str) -> str:
    """Convert MM/DD/YYYY to ISO YYYY-MM-DD format.

    Args:
        date_str: Date in ``MM/DD/YYYY`` format.

    Returns:
        Date in ``YYYY-MM-DD`` format.
    """
    month, day, year = date_str.split("/")
    return f"{year}-{month}-{day}"


def _parse_score(raw_score: str) -> tuple[float, float, float]:
    """Parse a score string like ``"5/5 = 100%"`` or ``"10.74/10 = 107.4%"``.

    Args:
        raw_score: The raw score string from the email.

    Returns:
        Tuple of (points_earned, points_possible, percentage).
    """
    match = re.match(
        r"([\d.]+)/([\d.]+)\s*=\s*([\d.]+)%",
        raw_score,
    )
    if match:
        return (
            float(match.group(1)),
            float(match.group(2)),
            float(match.group(3)),
        )
    return (0.0, 0.0, 0.0)


def _parse_assignments(body: str) -> list[Assignment]:
    """Parse all assignment lines from the email body.

    Handles normal graded lines, exempt (^), not-included (*),
    and not-yet-graded (* with -/N score) assignments.

    Args:
        body: The full email body text.

    Returns:
        List of parsed Assignment objects.
    """
    assignments: list[Assignment] = []

    # First, parse not-yet-graded lines (Grade: *   (-/N))
    not_yet_graded_names: set[str] = set()
    for match in _NOT_YET_GRADED_RE.finditer(body):
        date_str, raw_name, possible_str = (
            match.group(1),
            match.group(2),
            match.group(3),
        )
        name = raw_name.strip()
        not_yet_graded_names.add(name)
        assignments.append(
            Assignment(
                date=_convert_date(date_str),
                name=name,
                letter_grade="*",
                points_earned=0.0,
                points_possible=float(possible_str),
                percentage=0.0,
                is_missing=False,
                is_exempt=False,
                is_not_included=False,
                is_not_yet_graded=True,
            )
        )

    # Then, parse normal assignment lines
    for match in _ASSIGNMENT_RE.finditer(body):
        date_str = match.group(1)
        raw_name = match.group(2).strip()
        letter_grade = match.group(3)
        raw_score = match.group(4)

        # Skip if already handled as not-yet-graded
        name = raw_name.lstrip("^*").strip()
        if name in not_yet_graded_names:
            continue

        is_exempt = raw_name.startswith("^")
        is_not_included = raw_name.startswith("*")

        points_earned, points_possible, percentage = _parse_score(raw_score)

        is_missing = (
            points_earned == 0.0
            and points_possible > 0.0
            and not is_exempt
            and not is_not_included
        )

        assignments.append(
            Assignment(
                date=_convert_date(date_str),
                name=name,
                letter_grade=letter_grade,
                points_earned=points_earned,
                points_possible=points_possible,
                percentage=percentage,
                is_missing=is_missing,
                is_exempt=is_exempt,
                is_not_included=is_not_included,
                is_not_yet_graded=False,
            )
        )

    # Sort by date to maintain order
    assignments.sort(key=lambda a: a.date)
    return assignments


def parse_email_body(body: str) -> ParsedEmail:
    """Parse a single PowerSchool grade report email body.

    Args:
        body: The plain text body of the email.

    Returns:
        ParsedEmail containing student info and course data.
    """
    student = _parse_header(body, "Student")
    grading_period = _parse_header(body, "Grading period")
    course_name = _parse_header(body, "Course")
    period = _parse_header(body, "Period")
    instructor = _parse_header(body, "Instructor")
    overall_grade = _parse_overall_grade(body)
    assignments = _parse_assignments(body)

    return ParsedEmail(
        student=student,
        grading_period=grading_period,
        course=Course(
            name=course_name,
            period=period,
            instructor=instructor,
            overall_grade=overall_grade,
            assignments=assignments,
        ),
    )


def _extract_plain_text(msg: Message) -> str:
    """Extract plain text body from an email message.

    Handles both single-part and multi-part messages.

    Args:
        msg: Parsed email message object.

    Returns:
        The plain text body content.
    """
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if isinstance(payload, bytes):
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset)
        return ""

    if msg.get_content_type() != "text/plain":
        return ""
    payload = msg.get_payload(decode=True)
    if isinstance(payload, bytes):
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset)
    return ""


def fetch_emails(
    gmail_address: str,
    gmail_password: str,
    days_back: int = 7,
) -> GradeReport:
    """Fetch PowerSchool grade report emails from Gmail via IMAP.

    Args:
        gmail_address: Gmail address to connect to.
        gmail_password: Gmail app password for IMAP auth.
        days_back: Number of days to look back for emails.

    Returns:
        GradeReport assembled from parsed emails.
    """
    since = datetime.now(UTC) - timedelta(days=days_back)
    since_date = since.strftime("%d-%b-%Y")

    conn = imaplib.IMAP4_SSL(_IMAP_HOST)
    conn.login(gmail_address, gmail_password)

    try:
        conn.select(_GMAIL_ALL_MAIL)
        logger.info("Selected mailbox: %s", _GMAIL_ALL_MAIL)
    except imaplib.IMAP4.error:
        conn.select("INBOX")
        logger.info("Selected mailbox: INBOX (All Mail unavailable)")

    search_criteria = f'(FROM "{_SENDER}" SINCE "{since_date}")'
    logger.debug("IMAP search: %s", search_criteria)
    _status, msg_ids = conn.search(None, search_criteria)

    uid_list = msg_ids[0].split() if msg_ids[0] else []
    logger.info(
        "Found %d emails from '%s' since %s",
        len(uid_list),
        _SENDER,
        since_date,
    )

    parsed_courses: dict[str, ParsedEmail] = {}
    student = ""
    grading_period = ""

    for uid in uid_list:
        _status, msg_data = conn.fetch(uid, "(RFC822)")
        raw_msg = msg_data[0]
        if not isinstance(raw_msg, tuple):
            continue
        raw_email = raw_msg[1]
        if not isinstance(raw_email, bytes):
            continue
        msg = email.message_from_bytes(raw_email)
        body = _extract_plain_text(msg)

        if not body:
            continue

        parsed = parse_email_body(body)
        student = parsed.student
        grading_period = parsed.grading_period
        # Dedup by course name — last one wins (most recent)
        parsed_courses[parsed.course.name] = parsed

    conn.logout()

    return GradeReport(
        last_updated=datetime.now(UTC).isoformat(),
        student=student,
        grading_period=grading_period,
        courses=[p.course for p in parsed_courses.values()],
    )


def fetch_and_parse(gmail_address: str, gmail_password: str) -> GradeReport:
    """Fetch emails from Gmail and parse grade data.

    Args:
        gmail_address: Gmail address to connect to.
        gmail_password: Gmail app password for IMAP auth.

    Returns:
        Parsed GradeReport with all courses and assignments.
    """
    return fetch_emails(gmail_address, gmail_password)


def save_grade_report(report: GradeReport, output_path: str) -> None:
    """Write a GradeReport to a JSON file.

    Args:
        report: The grade report to save.
        output_path: File path to write the JSON output.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
