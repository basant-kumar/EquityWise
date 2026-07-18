"""Tests for the combined annual RSU and FA report command."""

from unittest.mock import patch

from click.testing import CliRunner

from equitywise.main import (
    _financial_year_to_fa_calendar_year,
    calculate_fa,
    calculate_rsu,
    cli,
)


def test_financial_year_maps_to_schedule_fa_calendar_year():
    assert _financial_year_to_fa_calendar_year("FY25-26") == 2025
    assert _financial_year_to_fa_calendar_year("fy24-25") == 2024


def test_generate_reports_invokes_both_existing_commands():
    runner = CliRunner()

    with (
        patch.object(calculate_rsu, "callback") as rsu_callback,
        patch.object(calculate_fa, "callback") as fa_callback,
    ):
        result = runner.invoke(
            cli,
            [
                "generate-reports",
                "--financial-year",
                "FY25-26",
                "--output-format",
                "both",
                "--validate-first",
                "--validate",
                "--export-fa-csv",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "FA calendar year 2025" in result.output
    rsu_callback.assert_called_once_with(
        financial_year="FY25-26",
        detailed=True,
        output_format="both",
        validate_first=True,
        validate=True,
    )
    fa_callback.assert_called_once_with(
        calendar_year=2025,
        detailed=True,
        output_format="both",
        validate_first=True,
        export_fa_csv=True,
        validate=True,
    )


def test_generate_reports_defaults_to_complete_validated_output():
    runner = CliRunner()

    with (
        patch.object(calculate_rsu, "callback") as rsu_callback,
        patch.object(calculate_fa, "callback") as fa_callback,
    ):
        result = runner.invoke(
            cli, ["generate-reports", "--financial-year", "FY25-26"]
        )

    assert result.exit_code == 0, result.output
    rsu_callback.assert_called_once_with(
        financial_year="FY25-26",
        detailed=True,
        output_format="both",
        validate_first=False,
        validate=True,
    )
    fa_callback.assert_called_once_with(
        calendar_year=2025,
        detailed=True,
        output_format="both",
        validate_first=False,
        export_fa_csv=False,
        validate=True,
    )


def test_help_recommends_the_single_combined_command():
    runner = CliRunner()

    root_help = runner.invoke(cli, ["--help"])
    assert root_help.exit_code == 0
    assert "RECOMMENDED - ONE COMMAND FOR A FINANCIAL YEAR" in root_help.output
    assert "generate-reports --financial-year FY25-26" in root_help.output

    command_help = runner.invoke(cli, ["generate-reports", "--help"])
    assert command_help.exit_code == 0
    assert "detailed Excel and CSV reports" in command_help.output
    assert "--validate / --no-validate" in command_help.output
    assert "default: validate" in command_help.output


def test_generate_reports_rejects_invalid_or_unsupported_fy():
    runner = CliRunner()

    invalid = runner.invoke(
        cli, ["generate-reports", "--financial-year", "FY25-27"]
    )
    assert invalid.exit_code == 2
    assert "expected FY<YY>-<YY>" in invalid.output

    unsupported = runner.invoke(
        cli, ["generate-reports", "--financial-year", "FY17-18"]
    )
    assert unsupported.exit_code == 2
    assert "FY18-19 through FY30-31" in unsupported.output
