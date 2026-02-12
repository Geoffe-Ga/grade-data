"""CLI entrypoint: fetch PowerSchool emails and write grades.json."""

import logging
import os
import sys

from grade_data.parser import fetch_and_parse, save_grade_report

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the email parser pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    gmail_address = os.environ.get("GMAIL_ADDRESS", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_address or not gmail_password:
        logger.error("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set")
        sys.exit(1)

    try:
        report = fetch_and_parse(gmail_address, gmail_password)
    except Exception:
        logger.exception("Failed to fetch emails")
        sys.exit(2)

    save_grade_report(report, "grades.json")
    logger.info(
        "Saved grades for %s (%d courses)",
        report.student,
        len(report.courses),
    )


if __name__ == "__main__":
    main()
