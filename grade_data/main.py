"""Main entry point for grade-data."""

from grade_data.models import GradeReport


def main() -> None:
    """Run the main application."""
    report = GradeReport(
        last_updated="",
        student="Layla H.",
        grading_period="Q3",
    )
    print(f"grade-data: tracking grades for {report.student}")


if __name__ == "__main__":
    main()
