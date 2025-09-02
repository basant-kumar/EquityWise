"""Basic tests for RSU FA Tool."""

import pytest
from datetime import date

from rsu_fa_tool.utils.date_utils import get_financial_year_dates, get_calendar_year_dates
from rsu_fa_tool.utils.currency_utils import format_currency, calculate_gain_loss


def test_financial_year_dates():
    """Test financial year date calculation."""
    start, end = get_financial_year_dates("FY2024")
    assert start == date(2023, 4, 1)
    assert end == date(2024, 3, 31)


def test_calendar_year_dates():
    """Test calendar year date calculation."""
    start, end = get_calendar_year_dates(2024)
    assert start == date(2024, 1, 1)
    assert end == date(2024, 12, 31)


def test_format_currency():
    """Test currency formatting."""
    assert format_currency(1000.50, "INR") == "₹1,000.50"
    assert format_currency(1000.50, "USD") == "$1,000.50"


def test_calculate_gain_loss():
    """Test gain/loss calculation."""
    result = calculate_gain_loss(150.0, 100.0)
    assert result["gain_loss_amount"] == 50.0
    assert result["gain_loss_percent"] == 50.0
    assert result["is_gain"] is True
