"""Regression tests for auto-detected bank statement layouts."""

from datetime import date

from openpyxl import Workbook

from equitywise.data.loaders import BankStatementLoader


def _save_axis_statement(path):
    workbook = Workbook()
    sheet = workbook.active
    for _ in range(16):
        sheet.append(["Statement metadata"])
    sheet.append([
        "SRL NO", "Tran Date", "CHQNO", "PARTICULARS", "DR", "CR", "BAL", "SOL"
    ])
    sheet.append([
        1, "24-08-2025", "-", "SALARY CREDIT", 0, "1,234.50", "12,345.00", "001"
    ])
    workbook.save(path)


def _save_icici_statement(path):
    workbook = Workbook()
    sheet = workbook.active
    for _ in range(12):
        sheet.append(["Statement metadata"])
    sheet.append([
        None, "S No.", "Value Date", "Transaction Date", "Cheque Number",
        "Transaction Remarks", "Withdrawal Amount(INR)", "Deposit Amount(INR)",
        "Balance(INR)",
    ])
    sheet.append([
        None, 1, "03/05/2025", "03/05/2025", "-",
        "IRM/USD6213.87@87.0375GST576/INREM/20250503115415",
        0, 540264.0, 1234567.89,
    ])
    workbook.save(path)


def test_axis_bank_statement_column_aliases(tmp_path):
    statement_path = tmp_path / "AxisBankStatement.xlsx"
    _save_axis_statement(statement_path)

    records = BankStatementLoader(statement_path).get_validated_records()

    assert len(records) == 1
    record = records[0]
    assert record.transaction_date == date(2025, 8, 24)
    assert record.value_date == date(2025, 8, 24)
    assert record.deposit_amount == 1234.50
    assert record.balance == 12345.00


def test_icici_bank_statement_and_broker_detection(tmp_path):
    statement_path = tmp_path / "ICICIBankStatement.xlsx"
    _save_icici_statement(statement_path)

    records = BankStatementLoader(statement_path).get_validated_records()

    assert len(records) == 1
    assert records[0].is_broker_transaction
    details = records[0].extract_broker_details()
    assert details is not None
    assert details["bank_usd_amount"] == 6213.87
    assert details["bank_exchange_rate"] == 87.0375
