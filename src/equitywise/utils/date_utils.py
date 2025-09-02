"""Date handling utilities for RSU FA Tool."""

from datetime import date, datetime
from typing import Optional, Tuple

from dateutil.relativedelta import relativedelta


def get_financial_year_dates(fy_string: Optional[str] = None) -> Tuple[date, date]:
    """Get start and end dates for a financial year.
    
    Args:
        fy_string: Financial year string like 'FY2024'. If None, uses current FY.
        
    Returns:
        Tuple of (start_date, end_date) for the financial year.
        
    Note:
        Indian Financial Year runs from April 1 to March 31.
    """
    if fy_string:
        # Extract year from FY string (e.g., 'FY2024' -> 2024 or 'FY24-25' -> 2025)
        fy_part = fy_string.replace('FY', '')
        if '-' in fy_part:
            # New format: FY24-25 -> use end year (25 -> 2025)
            end_year_short = int(fy_part.split('-')[1])
            year = 2000 + end_year_short if end_year_short < 50 else 1900 + end_year_short
        else:
            # Old format: FY2024 -> use as-is
            year = int(fy_part)
        
        start_date = date(year - 1, 4, 1)  # April 1 of previous year
        end_date = date(year, 3, 31)       # March 31 of the year
    else:
        # Determine current financial year
        today = date.today()
        if today.month >= 4:  # April to December - current FY
            start_date = date(today.year, 4, 1)
            end_date = date(today.year + 1, 3, 31)
        else:  # January to March - previous FY
            start_date = date(today.year - 1, 4, 1)
            end_date = date(today.year, 3, 31)
    
    return start_date, end_date


def get_calendar_year_dates(year: Optional[int] = None) -> Tuple[date, date]:
    """Get start and end dates for a calendar year.
    
    Args:
        year: Calendar year. If None, uses current year.
        
    Returns:
        Tuple of (start_date, end_date) for the calendar year.
    """
    if year is None:
        year = date.today().year
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    return start_date, end_date


def parse_date_string(date_str: str, formats: Optional[list[str]] = None) -> date:
    """Parse a date string using common formats.
    
    Args:
        date_str: Date string to parse.
        formats: List of date formats to try. If None, uses common formats.
        
    Returns:
        Parsed date object.
        
    Raises:
        ValueError: If date string cannot be parsed.
    """
    if formats is None:
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y", 
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
        ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date string: {date_str}")


def is_date_in_range(check_date: date, start_date: date, end_date: date) -> bool:
    """Check if a date falls within a given range (inclusive).
    
    Args:
        check_date: Date to check.
        start_date: Start of the range.
        end_date: End of the range.
        
    Returns:
        True if date is in range, False otherwise.
    """
    return start_date <= check_date <= end_date


def get_quarter_dates(year: int, quarter: int) -> Tuple[date, date]:
    """Get start and end dates for a specific quarter.
    
    Args:
        year: Year.
        quarter: Quarter number (1-4).
        
    Returns:
        Tuple of (start_date, end_date) for the quarter.
        
    Raises:
        ValueError: If quarter is not between 1 and 4.
    """
    if not 1 <= quarter <= 4:
        raise ValueError("Quarter must be between 1 and 4")
    
    start_month = (quarter - 1) * 3 + 1
    start_date = date(year, start_month, 1)
    end_date = start_date + relativedelta(months=3) - relativedelta(days=1)
    
    return start_date, end_date
