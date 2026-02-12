"""Tests for grade_data.main module."""

from grade_data.main import main


def test_main_runs(capsys) -> None:
    """Test that main() runs and prints the expected output."""
    main()
    captured = capsys.readouterr()
    assert "Layla H." in captured.out
