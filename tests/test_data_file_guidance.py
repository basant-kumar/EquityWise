from pathlib import Path

import pandas as pd
import pytest

from equitywise.data.loaders import (
    BenefitHistoryLoader,
    GLStatementLoader,
    UnsupportedExpandedExportError,
)


def test_benefit_history_missing_column_shows_expanded_download_guidance(
    monkeypatch,
):
    collapsed = pd.DataFrame(
        columns=["Record Type", "Symbol", "Grant Date"]
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: collapsed)

    with pytest.raises(UnsupportedExpandedExportError) as exc_info:
        BenefitHistoryLoader(Path("BenefitHistory.xlsx"))._load_file()

    message = str(exc_info.value)
    assert "missing required column(s): 'Vest Date'" in message
    assert "Possible fixes:" in message
    assert "Benefit History → Download Expanded" in message
    assert "collapsed or summary" in message


def test_gl_missing_columns_shows_expanded_download_guidance(monkeypatch):
    collapsed = pd.DataFrame(
        columns=["Record Type", "Quantity", "Date Sold", "Total Proceeds"]
    )
    monkeypatch.setattr(pd, "read_excel", lambda *args, **kwargs: collapsed)

    with pytest.raises(UnsupportedExpandedExportError) as exc_info:
        GLStatementLoader(Path("G&L_2025.xlsx"))._load_file()

    message = str(exc_info.value)
    assert "missing required column(s)" in message
    assert "Possible fixes:" in message
    assert "Gains & Losses" in message
    assert "Download Expanded" in message
    assert "G&L_Expanded_YYYY.xlsx" in message


def test_unrelated_excel_error_does_not_show_download_guidance(monkeypatch):
    def fail_to_open(*args, **kwargs):
        raise PermissionError("workbook is locked")

    monkeypatch.setattr(pd, "read_excel", fail_to_open)

    with pytest.raises(PermissionError) as exc_info:
        BenefitHistoryLoader(Path("BenefitHistory.xlsx"))._load_file()

    message = str(exc_info.value)
    assert message == "workbook is locked"
    assert "Possible fixes:" not in message
    assert "Download Expanded" not in message
