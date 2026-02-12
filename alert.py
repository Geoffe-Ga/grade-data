"""CLI entrypoint: compare grades against state and send Discord alerts."""

import json
import logging
import os
import sys

from grade_data.alerter import (
    load_alert_state,
    save_alert_state,
    send_alerts,
)
from grade_data.models import GradeReport

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the Discord alert pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    dashboard_url = os.environ.get("DASHBOARD_URL", "")

    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL must be set")
        sys.exit(1)

    grades_path = "grades.json"
    if not os.path.exists(grades_path):
        logger.error("grades.json not found — run parse_emails.py first")
        sys.exit(1)

    with open(grades_path) as f:
        grade_data = json.load(f)

    report = GradeReport.from_dict(grade_data)
    state = load_alert_state("state.json")

    try:
        updated_state = send_alerts(report, state, webhook_url, dashboard_url)
    except Exception:
        logger.exception("Failed to send alerts")
        sys.exit(2)

    save_alert_state(updated_state, "state.json")
    logger.info("Alert check complete")


if __name__ == "__main__":
    main()
