"""
Validation module for EquityWise calculations.

This module provides comprehensive validation capabilities including:
- Cross-validation between RSU and FA calculations
- Data source consistency checking
- Internal calculation validation
- Detailed validation reporting

Classes:
    CrossValidator: Main validation class
    ValidationResult: Validation results container
    ValidationError: Individual validation error representation
"""

from .cross_validator import CrossValidator, ValidationResult, ValidationError

__all__ = [
    "CrossValidator",
    "ValidationResult", 
    "ValidationError"
]
