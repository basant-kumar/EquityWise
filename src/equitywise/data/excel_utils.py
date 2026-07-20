"""Shared helpers for reading multi-sheet Excel workbooks.

Kept separate from ``loaders`` and ``rsu_parser`` so both can import it
without creating a circular dependency (``loaders`` imports ``rsu_parser``).
"""

from typing import Callable, List, Optional, Sequence

import pandas as pd


def select_sheet_by_name(
    xls: pd.ExcelFile,
    preferred_names: Sequence[str],
    required_columns: Optional[Sequence[str]] = None,
    header_matcher: Optional[Callable[[List[object]], bool]] = None,
) -> str:
    """Pick a worksheet by name/content, never by positional index.

    Brokers occasionally reorder or add sheets between exports -- e.g.
    BenefitHistory.xlsx shipping an 'ESPP' sheet before 'Restricted Stock' --
    so blindly reading ``sheet_name=0`` can silently load the wrong tab and
    fail downstream column checks. This resolves the sheet in three passes,
    each still keyed off the sheet *name* or its contents:

    1. Exact (case-insensitive) match against ``preferred_names``.
    2. Scan each sheet's header row and pick the first one that matches:
       ``header_matcher`` if given (for flexible/aliased column layouts),
       otherwise all of ``required_columns`` (exact subset match).
    3. Fall back to the first sheet name in the workbook
       (``xls.sheet_names[0]``) -- still a name lookup, just the first one,
       used only when neither heuristic above finds a match.
    """
    normalized_preferred = {name.strip().lower() for name in preferred_names}
    for name in xls.sheet_names:
        if name.strip().lower() in normalized_preferred:
            return name

    if header_matcher is not None or required_columns:
        for name in xls.sheet_names:
            try:
                header = pd.read_excel(xls, sheet_name=name, nrows=0)
            except Exception:
                continue
            columns = list(header.columns)
            if header_matcher is not None:
                if header_matcher(columns):
                    return name
            elif set(required_columns).issubset(set(columns)):
                return name

    return xls.sheet_names[0]
