"""Tests for PDF and Excel RSU statement ingestion."""

from datetime import date, datetime

from openpyxl import Workbook

from equitywise.calculators.rsu_calculator import RSUCalculator
from equitywise.config.settings import Settings
from equitywise.data.loaders import RSULoader
from equitywise.data.rsu_parser import RSUParser


def _statement_line() -> str:
    return (
        "RSU RU403833 $0.00 2 15-01-2025 $419.49 $838.98 "
        "86.3632 72457 0 $419.49 86.3632 $0.00 0 72,457.00"
    )


def test_excel_statement_is_parsed_into_rsu_records(tmp_path):
    statement_path = tmp_path / "RSU_FY-24-25.xlsx"
    workbook = Workbook()
    details = workbook.active
    details.title = "Statement"
    details.append([
        "Type", "Grant", "Grant Price", "Quantity", "", "Vesting Date",
        "FMV USD", "Total USD", "Forex", "Total INR", "WH Quantity",
        "WH FMV USD", "WH Forex", "WH Total USD", "WH Total INR", "Net INR",
    ])
    details.append([
        "RSU", "RU403833", 0, 3, "NA", datetime(2025, 1, 15),
        304.53, 913.59, 90.2935, 82491, 1, 304.53, 90.2935,
        304.53, 27497, 109988,
    ])
    workbook.save(statement_path)

    records = RSUParser(str(statement_path)).extract_vesting_data()

    assert len(records) == 1
    record = records[0]
    assert record.employee_id is None
    assert record.employee_name is None
    assert record.grant_number == "RU403833"
    assert record.grant_type == "RSU"
    assert record.quantity == 4
    assert record.vesting_date == date(2025, 1, 15)
    assert record.fmv_usd == 304.53
    assert record.total_usd == 1218.12
    assert record.forex_rate == 90.2935
    assert record.total_inr == 109988
    assert record.wh_quantity == 1
    assert record.wh_total_inr == 27497

    event = RSUCalculator([], []).process_rsu_vesting_events(records)[0]
    assert event.vested_quantity == 4
    assert event.taxable_gain_usd == 1218.12
    assert event.taxable_gain_inr == 109988

    loaded = RSULoader(statement_path).load_data()
    assert loaded.loc[0, "grant_number"] == "RU403833"
    assert loaded.loc[0, "vesting_date"] == date(2025, 1, 15)


def test_pdf_statement_continues_to_use_existing_row_format(tmp_path, monkeypatch):
    statement_path = tmp_path / "RSU_FY-24-25.pdf"
    statement_path.touch()

    class FakePage:
        def extract_text(self):
            return f"Employee Id 12345 Employee Name Ada Lovelace\n{_statement_line()}"

    class FakePDF:
        pages = [FakePage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr("equitywise.data.rsu_parser.pdfplumber.open", lambda _: FakePDF())

    records = RSUParser(str(statement_path)).extract_vesting_data()

    assert len(records) == 1
    assert records[0].grant_number == "RU403833"
    assert records[0].vesting_date == date(2025, 1, 15)


def test_rsu_discovery_accepts_pdf_and_excel_statements(tmp_path):
    for filename in [
        "RSU_FY-22-23.pdf",
        "RSU_FY-23-24.xlsx",
        "RSU_FY-24-25.XLS",
        "RSU_FY-25-26.xlsm",
        "~$RSU_FY-25-26.xlsx",
        "notes.txt",
    ]:
        (tmp_path / filename).touch()

    settings = Settings(rsu_documents_dir=tmp_path)

    expected_statements = [
        "RSU_FY-22-23.pdf",
        "RSU_FY-23-24.xlsx",
        "RSU_FY-24-25.XLS",
        "RSU_FY-25-26.xlsm",
    ]
    assert [path.name for path in settings.discover_rsu_statement_files()] == expected_statements
    assert [path.name for path in settings.get_rsu_files()] == expected_statements
    assert [path.name for path in settings.discover_rsu_pdf_files()] == [
        "RSU_FY-22-23.pdf"
    ]


def test_bank_statement_getter_uses_auto_discovery(tmp_path):
    bank_dir = tmp_path / "bank_statements"
    bank_dir.mkdir()
    (bank_dir / "AxisBankStatement.xls").touch()
    (bank_dir / "ICICIBankStatement.xlsx").touch()
    (bank_dir / "~$temporary.xlsx").touch()

    settings = Settings(bank_statements_dir=bank_dir)

    assert [path.name for path in settings.get_bank_statement_files()] == [
        "AxisBankStatement.xls",
        "ICICIBankStatement.xlsx",
    ]
