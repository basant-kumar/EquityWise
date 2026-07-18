"""Backward-compatible exports for the former ESOP statement parser.

RSU, ESOP, and ESPP statement rows now share the generalized parser model in
``rsu_parser``. This module keeps older imports working without duplicating the
parsing or validation implementation.
"""

from .rsu_parser import (
    RSUParser,
    RSUVestingRecord,
    parse_rsu_excel,
    parse_rsu_pdf,
    parse_rsu_statement,
)

ESOPVestingRecord = RSUVestingRecord
ESOPStatementParser = RSUParser
parse_esop_excel = parse_rsu_excel
parse_esop_pdf = parse_rsu_pdf
parse_esop_statement = parse_rsu_statement

__all__ = [
    "ESOPStatementParser",
    "ESOPVestingRecord",
    "parse_esop_excel",
    "parse_esop_pdf",
    "parse_esop_statement",
]
