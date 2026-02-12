"""CLI entrypoint: build the static HTML dashboard from grades.json."""

import json
import logging
import os
import sys

from grade_data.dashboard import build_dashboard
from grade_data.models import GradeReport

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the dashboard build pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    password_hash = os.environ.get("DASHBOARD_PASSWORD_HASH", "")

    if not password_hash:
        logger.error("DASHBOARD_PASSWORD_HASH must be set")
        sys.exit(1)

    grades_path = "grades.json"
    if not os.path.exists(grades_path):
        logger.error("grades.json not found — run parse_emails.py first")
        sys.exit(1)

    with open(grades_path) as f:
        grade_data = json.load(f)

    report = GradeReport.from_dict(grade_data)

    try:
        build_dashboard(report, password_hash)
    except Exception:
        logger.exception("Failed to build dashboard")
        sys.exit(2)

    logger.info("Dashboard built at docs/index.html")


if __name__ == "__main__":
    main()
