"""Regression tests for Foreign Assets report summaries."""

import csv
from datetime import date

from openpyxl import load_workbook

from equitywise.calculators.fa_calculator import FADeclarationSummary
from equitywise.reports.csv_reporter import CSVReporter
from equitywise.reports.excel_reporter import ExcelReporter


def test_fa_reports_use_peak_balance_for_declaration_requirement(tmp_path):
    summary = FADeclarationSummary(
        declaration_date=date(2026, 7, 18),
        calendar_year="2025",
        closing_balance_inr=150_000.0,
        peak_balance_inr=300_000.0,
        vested_holdings_inr=150_000.0,
    )

    csv_file = CSVReporter(tmp_path).generate_fa_report(
        summary, calendar_year="2025", detailed=False
    )[0]
    with csv_file.open(newline="", encoding="utf-8") as handle:
        declaration_row = next(
            row for row in csv.reader(handle) if row[1] == "Declaration Required?"
        )
    assert declaration_row[2] == "YES"

    excel_file = ExcelReporter(tmp_path).generate_fa_report(
        summary, calendar_year="2025", detailed=False
    )
    workbook = load_workbook(excel_file, data_only=True)
    rows = workbook["FA Summary"].iter_rows(values_only=True)
    declaration_row = next(row for row in rows if row[1] == "Declaration Required?")
    assert declaration_row[2] == "YES"
