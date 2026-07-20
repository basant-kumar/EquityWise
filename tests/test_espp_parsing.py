"""ESPP parsing and validation tests using synthetic (dummy) data.

No real ESPP data exists in this repo, so these tests exercise the ESPP
path of RSUParser end-to-end with the exact line formats documented in
src/equitywise/data/rsu_parser.py (lines 172-174) and the Excelity XLSX
column layout used by _XLSX_COL_MAP.
"""

from datetime import date

import pandas as pd
import pytest
from loguru import logger
from pydantic import ValidationError

from equitywise.data.rsu_parser import RSUParser, RSUVestingRecord

EMPLOYEE_LINE = "Employee Id : 123456 Employee Name : Test Employee"

# Formats documented in rsu_parser.py:172-174
ESPP_STANDARD = (
    "ESPP 03 $ 255.8245 14 NA 31-12-2019 $ 328.03 $ 1010.877 "
    "71.274 72049 0 $ 328.03 71.274 $ 0 0 72049"
)
ESPP_ATTACHED = (
    "ESPP 2020 $255.8245 16 NA 30-06-2020 $430.995 $2802.728 "
    "75.527 211682 0 $430.995 75.527 $0 0 211682"
)
ESPP_FRACTIONAL = (
    "ESPP 2024 $ 425.50 19.15 NA 30-06-2024 $ 500.25 $ 9579.79 "
    "83.45 799434 0 $ 500.25 83.45 $ 0 0 799434"
)
RSU_LINE = (
    "RSU RU403833 3 15-01-2026 $ 512.34 $ 1537.02 85.90 132030 "
    "1 $ 512.34 85.90 $ 44010 44010 132030"
)


def _parse(lines):
    parser = RSUParser("dummy.pdf")
    return parser._create_records_from_lines(lines, "espp-test")


# ---------------------------------------------------------------------------
# Text-line (PDF-style) parsing
# ---------------------------------------------------------------------------

class TestEsppLineParsing:
    def test_standard_format(self):
        (rec,) = _parse([EMPLOYEE_LINE, ESPP_STANDARD])
        assert rec.grant_type == "ESPP"
        assert rec.grant_number == "03"
        assert rec.grant_price_usd == pytest.approx(255.8245)
        assert rec.quantity == pytest.approx(14.0)
        assert rec.vesting_date == date(2019, 12, 31)
        assert rec.fmv_usd == pytest.approx(328.03)
        assert rec.forex_rate == pytest.approx(71.274)
        assert rec.total_inr == pytest.approx(72049.0)
        assert rec.wh_quantity == 0.0

    def test_attached_dollar_format(self):
        (rec,) = _parse([EMPLOYEE_LINE, ESPP_ATTACHED])
        assert rec.grant_type == "ESPP"
        assert rec.grant_number == "2020"
        assert rec.grant_price_usd == pytest.approx(255.8245)
        assert rec.quantity == pytest.approx(16.0)
        assert rec.vesting_date == date(2020, 6, 30)
        assert rec.fmv_usd == pytest.approx(430.995)

    def test_fractional_quantity_survives(self):
        """ESPP allows fractional purchases (e.g. 19.15 shares)."""
        (rec,) = _parse([EMPLOYEE_LINE, ESPP_FRACTIONAL])
        assert rec.quantity == pytest.approx(19.15)
        assert rec.vesting_date == date(2024, 6, 30)

    def test_mixed_rsu_and_espp(self):
        recs = _parse([EMPLOYEE_LINE, ESPP_STANDARD, RSU_LINE, ESPP_ATTACHED])
        types = [r.grant_type for r in recs]
        assert types == ["ESPP", "RSU", "ESPP"]
        rsu = recs[1]
        # RSUs never have a purchase price
        assert rsu.grant_price_usd is None
        assert rsu.grant_number == "RU403833"

    def test_employee_info_propagates(self):
        (rec,) = _parse([EMPLOYEE_LINE, ESPP_STANDARD])
        assert rec.employee_id == "123456"
        assert rec.employee_name == "Test Employee"


# ---------------------------------------------------------------------------
# Completeness validation (rsu_parser._validate_parsing_completeness)
# ---------------------------------------------------------------------------

class TestParsingCompletenessValidation:
    def _capture_logs(self, lines):
        messages = []
        sink_id = logger.add(lambda msg: messages.append(str(msg)), level="DEBUG")
        try:
            records = _parse(lines)
        finally:
            logger.remove(sink_id)
        return records, "".join(messages)

    def test_all_parsed_reports_success(self):
        records, logs = self._capture_logs([EMPLOYEE_LINE, ESPP_STANDARD, RSU_LINE])
        assert len(records) == 2
        assert "Parsing validation passed: 2/2" in logs
        assert "PARSING MISMATCH" not in logs

    def test_malformed_espp_line_triggers_mismatch_warning(self):
        bad_line = "ESPP 99 this line has no parseable date or numbers"
        records, logs = self._capture_logs([EMPLOYEE_LINE, ESPP_STANDARD, bad_line])
        # Only the good line parses...
        assert len(records) == 1
        # ...and the validator flags the discrepancy loudly.
        assert "PARSING MISMATCH: Expected 2 entries, but parsed 1" in logs
        assert "1 entries were NOT parsed successfully" in logs


# ---------------------------------------------------------------------------
# Pydantic model validation (RSUVestingRecord)
# ---------------------------------------------------------------------------

class TestRecordValidation:
    BASE = dict(
        grant_number="2024",
        grant_type="ESPP",
        quantity=19.15,
        vesting_date="30-06-2024",
        fmv_usd=500.25,
        total_usd=9579.79,
        forex_rate=83.45,
        total_inr=799434.0,
        grant_price_usd=425.50,
    )

    def test_valid_record_accepted(self):
        rec = RSUVestingRecord(**self.BASE)
        assert rec.vesting_date == date(2024, 6, 30)

    @pytest.mark.parametrize("field,value", [
        ("quantity", -5),
        ("quantity", 0),
        ("fmv_usd", -1.0),
        ("total_usd", -100.0),
        ("wh_quantity", -1),
        ("wh_total_inr", -50.0),
    ])
    def test_invalid_numeric_values_rejected(self, field, value):
        with pytest.raises(ValidationError):
            RSUVestingRecord(**{**self.BASE, field: value})

    def test_unparseable_date_rejected(self):
        with pytest.raises(ValidationError):
            RSUVestingRecord(**{**self.BASE, "vesting_date": "junk-date"})

    def test_comma_separated_quantity_parsed(self):
        rec = RSUVestingRecord(**{**self.BASE, "quantity": "1,234.5"})
        assert rec.quantity == pytest.approx(1234.5)


# ---------------------------------------------------------------------------
# XLSX (Excelity Stock Perquisites Statement) path
# ---------------------------------------------------------------------------

def _write_xlsx(path, rows):
    columns = [
        "Type of Plan", "Grant Number/Plan Number", "Grant Price in USD $",
        "Quantity", "Excercise Date(For ESOP Only)", "Vesting/Purchase Date",
        "FMV in USD $", "Total Perquisites in USD $", "Forex rates in USD $",
        "Total Perquisites in INR", "Equity WH (QTY)", "FMV (WH)",
        "Forex Rate (WH)", "WH Perquisites in USD", "Perq on Equity WH in (INR)",
        "Total Perquisites on form 16 (INR)",
    ]
    pd.DataFrame(rows, columns=columns).to_excel(path, index=False)


class TestEsppXlsxParsing:
    def test_espp_and_rsu_rows(self, tmp_path):
        f = tmp_path / "Stock_Perquisites.xlsx"
        _write_xlsx(f, [
            ["ESPP", "2024", 425.50, 19.15, None, "2024-06-30",
             500.25, 9579.79, 83.45, 799434.0, 0, 0, 0, 0, 0, 799434.0],
            ["RSU", "RU403833", None, 3, None, "2026-01-15",
             512.34, 1537.02, 85.90, 132030.0, 1, 512.34, 85.90, 512.34, 44010.0, 176040.0],
        ])
        records = RSUParser(str(f)).extract_vesting_data()
        assert len(records) == 2

        espp, rsu = records
        assert espp.grant_type == "ESPP"
        assert espp.grant_price_usd == pytest.approx(425.50)
        assert espp.quantity == pytest.approx(19.15)
        assert espp.vesting_date == date(2024, 6, 30)
        assert rsu.grant_type == "RSU"
        assert rsu.grant_price_usd is None

    def test_invalid_row_skipped_not_fatal(self, tmp_path):
        """A row failing pydantic validation (negative quantity) is skipped
        with a warning; the remaining valid rows still parse."""
        f = tmp_path / "Stock_Perquisites.xlsx"
        _write_xlsx(f, [
            ["ESPP", "2024", 425.50, -19.15, None, "2024-06-30",
             500.25, 9579.79, 83.45, 799434.0, 0, 0, 0, 0, 0, 799434.0],
            ["ESPP", "2025", 430.00, 10.0, None, "2025-06-30",
             520.00, 5200.00, 84.10, 437320.0, 0, 0, 0, 0, 0, 437320.0],
        ])
        records = RSUParser(str(f)).extract_vesting_data()
        assert len(records) == 1  # bad row rejected, good row kept
        assert records[0].grant_number == "2025"

    def test_unknown_plan_types_ignored(self, tmp_path):
        f = tmp_path / "Stock_Perquisites.xlsx"
        _write_xlsx(f, [
            ["ESOP", "E-1", 100.0, 5, "2024-01-15", "2024-01-15",
             200.0, 500.0, 83.0, 41500.0, 0, 0, 0, 0, 0, 41500.0],
            ["ESPP", "2024", 425.50, 19.15, None, "2024-06-30",
             500.25, 9579.79, 83.45, 799434.0, 0, 0, 0, 0, 0, 799434.0],
        ])
        records = RSUParser(str(f)).extract_vesting_data()
        assert [r.grant_type for r in records] == ["ESPP"]

    def test_missing_columns_yield_zero_records_with_mismatch_logged(self, tmp_path):
        """A sheet missing the numeric/date columns does not raise: the row
        cannot be line-parsed, so 0 records come back and the completeness
        validator logs a PARSING MISMATCH error."""
        f = tmp_path / "Stock_Perquisites.xlsx"
        df = pd.DataFrame([["ESPP", "2024"]], columns=["Type of Plan", "Grant Number/Plan Number"])
        df.to_excel(f, index=False)

        messages = []
        sink_id = logger.add(lambda m: messages.append(str(m)), level="DEBUG")
        try:
            records = RSUParser(str(f)).extract_vesting_data()
        finally:
            logger.remove(sink_id)
        logs = "".join(messages)
        assert records == []
        assert "PARSING MISMATCH: Expected 1 entries, but parsed 0" in logs
