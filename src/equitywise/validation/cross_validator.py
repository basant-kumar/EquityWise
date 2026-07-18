"""
Cross-validation module for RSU and FA calculations.

This module provides comprehensive validation between:
1. RSU (Financial Year) vs FA (Calendar Year) calculations for overlapping periods
2. BenefitHistory.xlsx vs RSU PDF vs G&L statement data consistency  
3. Calculation accuracy and data source integrity

Usage:
    validator = CrossValidator()
    validation_result = validator.validate_rsu_vs_fa(rsu_data, fa_data, year="2024")
    
    if not validation_result.is_valid:
        print("Validation failed!")
        for error in validation_result.errors:
            print(f"- {error}")
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
from decimal import Decimal

from ..data.models import (
    BenefitHistoryRecord, 
    GLStatementRecord,
    RSUTransaction
)
from ..calculators.rsu_calculator import VestingEvent, SaleEvent
from ..calculators.fa_calculator import VestWiseDetails, EquityHolding

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error with context."""
    category: str           # e.g., "Data Source", "Calculation", "Date Range"
    severity: str          # "ERROR", "WARNING", "INFO"  
    description: str       # Human readable description
    expected_value: Any = None
    actual_value: Any = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        if self.expected_value is not None and self.actual_value is not None:
            return f"[{self.severity}] {self.category}: {self.description} (Expected: {self.expected_value}, Got: {self.actual_value})"
        return f"[{self.severity}] {self.category}: {self.description}"


@dataclass
class ValidationResult:
    """Comprehensive validation result."""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, category: str, description: str, expected: Any = None, actual: Any = None, **context):
        """Add a validation error."""
        error = ValidationError("ERROR", category, description, expected, actual, context)
        self.errors.append(error)
        self.is_valid = False
        
    def add_warning(self, category: str, description: str, expected: Any = None, actual: Any = None, **context):
        """Add a validation warning."""
        warning = ValidationError("WARNING", category, description, expected, actual, context)
        self.warnings.append(warning)
    
    def get_error_count(self) -> int:
        return len(self.errors)
    
    def get_warning_count(self) -> int:
        return len(self.warnings)


class CrossValidator:
    """Comprehensive cross-validation system for RSU and FA calculations."""
    
    def __init__(self, tolerance: float = 0.01):
        """
        Initialize validator.
        
        Args:
            tolerance: Acceptable difference for monetary comparisons (as percentage)
        """
        self.tolerance = tolerance
        self.logger = logging.getLogger(__name__)
    
    def validate_comprehensive(
        self, 
        rsu_data: Dict[str, Any] = None,
        fa_data: Dict[str, Any] = None,
        benefit_history_records: List[BenefitHistoryRecord] = None,
        gl_records: List[GLStatementRecord] = None,
        rsu_pdf_records: List[RSUTransaction] = None,
        overlap_year: str = None,
        financial_year: str = None
    ) -> ValidationResult:
        """
        Perform comprehensive cross-validation across all data sources and calculations.
        
        Args:
            rsu_data: RSU calculation results
            fa_data: FA calculation results  
            benefit_history_records: Raw BenefitHistory records
            gl_records: G&L statement records
            rsu_pdf_records: RSU PDF transaction records
            overlap_year: Year to validate overlapping periods (e.g., "2024")
            
        Returns:
            ValidationResult with all validation results
        """
        result = ValidationResult(is_valid=True)
        
        self.logger.info("🔍 Starting comprehensive cross-validation...")
        
        # 1. Data Source Consistency Validation
        if benefit_history_records and rsu_pdf_records:
            self._validate_benefit_history_vs_rsu_pdf(
                result, benefit_history_records, rsu_pdf_records
            )
        
        if benefit_history_records and gl_records:
            self._validate_benefit_history_vs_gl_statements(
                result, benefit_history_records, gl_records
            )
        
        # 2. Cross-Calculation Validation (RSU vs FA)
        if rsu_data and fa_data and overlap_year:
            self._validate_rsu_vs_fa_overlap(result, rsu_data, fa_data, overlap_year)
        
        # 3. Internal Consistency Validation
        if rsu_data:
            self._validate_rsu_internal_consistency(result, rsu_data, financial_year)
            
        if fa_data:
            self._validate_fa_internal_consistency(result, fa_data)
        
        # 4. Generate validation summary
        result.summary = {
            "total_errors": result.get_error_count(),
            "total_warnings": result.get_warning_count(),
            "validation_categories": list(set(e.category for e in result.errors + result.warnings)),
            "validation_timestamp": datetime.now().isoformat()
        }
        
        if result.is_valid:
            self.logger.info("✅ Comprehensive validation passed!")
        else:
            self.logger.warning(f"❌ Validation failed with {result.get_error_count()} errors and {result.get_warning_count()} warnings")
        
        return result
    
    def _validate_benefit_history_vs_rsu_pdf(
        self, 
        result: ValidationResult,
        benefit_records: List[BenefitHistoryRecord],
        rsu_records: List[RSUTransaction]
    ):
        """Validate BenefitHistory.xlsx vs RSU PDF data consistency."""
        self.logger.info("Validating BenefitHistory vs RSU PDF consistency...")
        
        # Extract vesting events from BenefitHistory
        # Note: Based on user feedback, "Date" column = actual vesting date, "Event Type" = "Shares vested"
        benefit_vestings = {}
        for record in benefit_records:
            if (record.record_type == "Event" and 
                record.event_type == "Shares vested" and
                record.date and record.qty_or_amount):
                
                key = f"{record.grant_number}_{record.date}"
                quantity = record.qty_or_amount
                market_value = record.est_market_value or 0
                
                # Aggregate multiple vesting events for same grant on same date
                if key in benefit_vestings:
                    benefit_vestings[key]["quantity"] += quantity
                    benefit_vestings[key]["market_value"] += market_value
                    benefit_vestings[key]["transaction_count"] += 1
                else:
                    benefit_vestings[key] = {
                        "date": record.date,
                        "grant_number": record.grant_number,
                        "quantity": quantity,
                        "market_value": market_value,
                        "transaction_count": 1
                    }
        
        # Extract vesting events from RSU PDFs
        rsu_vestings = {}
        for record in rsu_records:
            key = f"{record.grant_number}_{record.vesting_date}"
            rsu_vestings[key] = {
                "date": record.vesting_date,
                "grant_number": record.grant_number,
                "quantity": record.quantity,
                "fmv_usd": record.fmv_usd,
                "total_usd": record.total_usd
            }
        
        # Compare vesting events
        all_keys = set(benefit_vestings.keys()) | set(rsu_vestings.keys())
        
        total_benefit_vesting_transactions = sum(v.get("transaction_count", 1) for v in benefit_vestings.values())
        
        self.logger.info(f"Found {len(benefit_vestings)} unique vesting dates from BenefitHistory ({total_benefit_vesting_transactions} individual transactions)")
        self.logger.info(f"Found {len(rsu_vestings)} vesting events from RSU PDFs")
        self.logger.info(f"Comparing {len(benefit_vestings)} BenefitHistory vs {len(rsu_vestings)} RSU PDF vesting events")
        
        for key in all_keys:
            benefit_vest = benefit_vestings.get(key)
            rsu_vest = rsu_vestings.get(key)
            
            if not benefit_vest:
                result.add_warning(
                    "Data Source Consistency",
                    f"Vesting event missing from BenefitHistory.xlsx but found in RSU PDF",
                    expected=f"Entry for {key}",
                    actual="Missing from BenefitHistory",
                    context={
                        "missing_from": "BenefitHistory.xlsx",
                        "present_in": "RSU PDF", 
                        "grant_date": key,
                        "rsu_pdf_details": {
                            "quantity": rsu_vest["quantity"],
                            "fmv_usd": rsu_vest.get("fmv_usd"),
                            "total_usd": rsu_vest.get("total_usd")
                        },
                        "recommendation": f"Check BenefitHistory.xlsx for vesting event on {rsu_vest['date']} for grant {rsu_vest['grant_number']}"
                    }
                )
            elif not rsu_vest:
                result.add_warning(
                    "Data Source Consistency", 
                    f"Vesting event missing from RSU PDF but found in BenefitHistory.xlsx",
                    expected=f"Entry for {key}",
                    actual="Missing from RSU PDF",
                    context={
                        "missing_from": "RSU PDF",
                        "present_in": "BenefitHistory.xlsx",
                        "grant_date": key, 
                        "benefit_history_details": {
                            "quantity": benefit_vest["quantity"],
                            "market_value": benefit_vest["market_value"]
                        },
                        "recommendation": f"Check RSU PDF for vesting event on {benefit_vest['date']} for grant {benefit_vest['grant_number']}"
                    }
                )
            else:
                # Compare quantities
                if not self._values_match(benefit_vest["quantity"], rsu_vest["quantity"]):
                    result.add_error(
                        "Data Source Consistency",
                        f"Vesting quantity mismatch between data sources",
                        expected=f"{rsu_vest['quantity']} shares (RSU PDF)",
                        actual=f"{benefit_vest['quantity']} shares (BenefitHistory)",
                        context={
                            "grant_number": rsu_vest["grant_number"],
                            "vesting_date": str(rsu_vest["date"]),
                            "rsu_pdf_data": {
                                "quantity": rsu_vest["quantity"],
                                "fmv_usd": rsu_vest.get("fmv_usd"),
                                "total_value_usd": rsu_vest.get("total_usd")
                            },
                            "benefit_history_data": {
                                "quantity": benefit_vest["quantity"], 
                                "market_value": benefit_vest["market_value"]
                            },
                            "discrepancy_analysis": f"Difference of {abs(float(rsu_vest['quantity']) - float(benefit_vest['quantity']))} shares",
                            "recommendation": f"Verify vesting records for grant {rsu_vest['grant_number']} on {rsu_vest['date']} in both RSU PDF and BenefitHistory.xlsx"
                        }
                    )
                
                # Compare market values if available
                if benefit_vest["market_value"] and rsu_vest["total_usd"]:
                    if not self._values_match(benefit_vest["market_value"], rsu_vest["total_usd"]):
                        result.add_warning(
                            "Data Source Consistency",
                            f"Market value mismatch between data sources",
                            expected=f"${rsu_vest['total_usd']:,.2f} USD (RSU PDF)",
                            actual=f"${benefit_vest['market_value']:,.2f} USD (BenefitHistory)",
                            context={
                                "grant_number": rsu_vest["grant_number"],
                                "vesting_date": str(rsu_vest["date"]),
                                "rsu_pdf_value": rsu_vest["total_usd"],
                                "benefit_history_value": benefit_vest["market_value"],
                                "percentage_difference": f"{abs((float(rsu_vest['total_usd']) - float(benefit_vest['market_value'])) / float(rsu_vest['total_usd']) * 100):.2f}%",
                                "recommendation": f"Check market value calculation methods - may be due to timing differences or different FMV sources"
                            }
                        )
    
    def _validate_benefit_history_vs_gl_statements(
        self,
        result: ValidationResult,
        benefit_records: List[BenefitHistoryRecord],
        gl_records: List[GLStatementRecord]
    ):
        """Validate BenefitHistory vs G&L statement consistency for sale events."""
        self.logger.info("Validating BenefitHistory vs G&L statement consistency...")
        
        # Extract sale events from BenefitHistory (if present)
        # Note: Based on user feedback, BenefitHistory "Date" column represents the actual date when event occurred
        # Only "Shares sold" events are actual sales - "Shares released" are NOT sales (they're vesting/release events)
        # Only include sales that are not in the future (compared to today)
        from datetime import date as today_date
        benefit_sales = {}
        for record in benefit_records:
            if (record.record_type == "Event" and 
                record.event_type and record.event_type.lower() == "shares sold" and  # Only actual sales
                record.date and record.qty_or_amount and
                record.date <= today_date.today()):  # Exclude future sales
                
                key = f"{record.grant_number}_{record.date}"
                quantity = abs(record.qty_or_amount)  # Sales might be negative
                
                # Aggregate multiple sales for same grant on same date
                if key in benefit_sales:
                    benefit_sales[key]["quantity"] += quantity
                    benefit_sales[key]["transaction_count"] += 1
                else:
                    benefit_sales[key] = {
                        "date": record.date,
                        "grant_number": record.grant_number,
                        "quantity": quantity,
                        "transaction_count": 1
                    }
        
        # Extract sale events from G&L statements
        gl_sales = {}
        for record in gl_records:
            if record.record_type == "Sell" and record.date_sold and record.quantity:
                key = f"{record.grant_number}_{record.date_sold}"
                
                # Aggregate multiple sales for same grant on same date
                if key in gl_sales:
                    gl_sales[key]["quantity"] += record.quantity
                    gl_sales[key]["proceeds"] += record.total_proceeds
                    gl_sales[key]["cost_basis"] += record.adjusted_cost_basis
                    gl_sales[key]["transaction_count"] += 1
                else:
                    gl_sales[key] = {
                        "date": record.date_sold,
                        "grant_number": record.grant_number,
                        "quantity": record.quantity,
                        "proceeds": record.total_proceeds,
                        "cost_basis": record.adjusted_cost_basis,
                        "transaction_count": 1
                    }
        
        # Compare sale events
        total_benefit_transactions = sum(s.get("transaction_count", 1) for s in benefit_sales.values())
        total_gl_transactions = sum(s.get("transaction_count", 1) for s in gl_sales.values())
        
        self.logger.info(f"Found {len(benefit_sales)} unique sale dates from BenefitHistory (Event Type='Shares sold' only) ({total_benefit_transactions} individual transactions)")
        self.logger.info(f"Found {len(gl_sales)} unique sale dates from G&L statements ({total_gl_transactions} individual transactions)")
        
        
        if benefit_sales:  # Only validate if BenefitHistory has sale data
            self.logger.info(f"Comparing {len(benefit_sales)} BenefitHistory vs {len(gl_sales)} G&L statement sale events")
            all_keys = set(benefit_sales.keys()) | set(gl_sales.keys())
            
            for key in all_keys:
                benefit_sale = benefit_sales.get(key)
                gl_sale = gl_sales.get(key)
                
                if not benefit_sale and gl_sale:
                    result.add_warning(
                        "Data Source Consistency",
                        f"Sale transaction missing from BenefitHistory.xlsx but found in G&L statement",
                        expected=f"Sale entry for {key}",
                        actual="Missing from BenefitHistory",
                        context={
                            "missing_from": "BenefitHistory.xlsx",
                            "present_in": "G&L Statement",
                            "transaction_key": key,
                            "gl_statement_details": {
                                "quantity": gl_sale["quantity"],
                                "proceeds": gl_sale.get("proceeds"),
                                "cost_basis": gl_sale.get("cost_basis"),
                                "sale_date": str(gl_sale["date"])
                            },
                            "recommendation": f"Check BenefitHistory.xlsx for sale event on {gl_sale['date']} for grant {gl_sale['grant_number']} - may indicate incomplete BenefitHistory data"
                        }
                    )
                elif benefit_sale and not gl_sale:
                    # Check if this might be due to G&L statement coverage period
                    sale_year = benefit_sale["date"].year
                    gl_years = set(r.date_sold.year for r in gl_records if r.date_sold)
                    
                    if sale_year not in gl_years:
                        # Different reporting periods - this is expected
                        result.add_warning(
                            "Data Coverage Difference",
                            f"Sale transaction from {sale_year} in BenefitHistory but G&L statements only cover years {sorted(gl_years)}",
                            expected=f"G&L data for year {sale_year}",
                            actual=f"G&L statements only cover {sorted(gl_years)}",
                            context={
                                "coverage_issue": True,
                                "sale_year": sale_year,
                                "gl_coverage_years": sorted(gl_years),
                                "grant_number": benefit_sale["grant_number"],
                                "sale_date": str(benefit_sale["date"]),
                                "quantity": benefit_sale["quantity"],
                                "recommendation": f"This is likely normal - G&L statements may not cover all historical periods in BenefitHistory"
                            }
                        )
                    else:
                        # Same year but missing - potential data issue
                        result.add_warning(
                            "Data Source Consistency",
                            f"Sale transaction missing from G&L statement but found in BenefitHistory.xlsx",
                            expected=f"Sale entry for {key}",
                            actual="Missing from G&L Statement",
                            context={
                                "missing_from": "G&L Statement", 
                                "present_in": "BenefitHistory.xlsx",
                                "transaction_key": key,
                                "benefit_history_details": {
                                    "quantity": benefit_sale["quantity"],
                                    "sale_date": str(benefit_sale["date"])
                                },
                                "recommendation": f"Check G&L statement for sale on {benefit_sale['date']} for grant {benefit_sale['grant_number']} - may indicate missing G&L data"
                            }
                        )
                elif benefit_sale and gl_sale:
                    # Compare quantities
                    if not self._values_match(benefit_sale["quantity"], gl_sale["quantity"]):
                        result.add_error(
                            "Data Source Consistency",
                            f"Sale quantity mismatch between data sources",
                            expected=f"{gl_sale['quantity']} shares (G&L Statement)",
                            actual=f"{benefit_sale['quantity']} shares (BenefitHistory)",
                            context={
                                "grant_number": gl_sale["grant_number"],
                                "sale_date": str(gl_sale["date"]),
                                "gl_statement_data": {
                                    "total_quantity": gl_sale["quantity"],
                                    "transaction_count": gl_sale.get("transaction_count", 1),
                                    "total_proceeds": gl_sale.get("proceeds"),
                                    "total_cost_basis": gl_sale.get("cost_basis")
                                },
                                "benefit_history_data": {
                                    "total_quantity": benefit_sale["quantity"],
                                    "transaction_count": benefit_sale.get("transaction_count", 1)
                                },
                                "discrepancy_analysis": f"Difference of {abs(float(gl_sale['quantity']) - float(benefit_sale['quantity']))} shares",
                                "transaction_aggregation": f"G&L: {gl_sale.get('transaction_count', 1)} transactions, BenefitHistory: {benefit_sale.get('transaction_count', 1)} transactions",
                                "recommendation": f"Multiple transactions on {gl_sale['date']} have been aggregated. Verify individual transaction details for grant {gl_sale['grant_number']} in both sources"
                            }
                        )
    
    def _validate_rsu_vs_fa_overlap(
        self,
        result: ValidationResult,
        rsu_data: Dict[str, Any],
        fa_data: Dict[str, Any], 
        overlap_year: str
    ):
        """Validate RSU vs FA calculations for overlapping periods."""
        self.logger.info(f"Validating RSU vs FA overlap for {overlap_year}...")
        
        # Parse overlap year
        try:
            year = int(overlap_year)
            
            # Define overlapping periods
            # FY24-25 (Apr 2024 - Mar 2025) vs CY2024 (Jan 2024 - Dec 2024) 
            # Overlap: Apr 2024 - Dec 2024 (9 months)
            fy_start = date(year, 4, 1)
            fy_end = date(year + 1, 3, 31) 
            cy_start = date(year, 1, 1)
            cy_end = date(year, 12, 31)
            
            # Overlapping period 
            overlap_start = max(fy_start, cy_start)  # April 1
            overlap_end = min(fy_end, cy_end)       # December 31
            
            self.logger.info(f"Overlap period: {overlap_start} to {overlap_end}")
            
            # Get RSU events in overlap period
            rsu_vestings_overlap = []
            rsu_sales_overlap = []
            
            if "vesting_events" in rsu_data:
                rsu_vestings_overlap = [
                    v for v in rsu_data["vesting_events"]
                    if overlap_start <= v.vest_date <= overlap_end
                ]
                
            if "sale_events" in rsu_data:
                rsu_sales_overlap = [
                    s for s in rsu_data["sale_events"] 
                    if overlap_start <= s.sale_date <= overlap_end
                ]
            
            # Get FA events in overlap period (should match)
            fa_vestings_overlap = []
            fa_sales_overlap = []
            
            if "vest_wise_details" in fa_data:
                fa_vestings_overlap = [
                    v for v in fa_data["vest_wise_details"]
                    if overlap_start <= v.vest_date <= overlap_end
                ]
            
            # Compare vesting events in overlap period
            self._compare_overlap_vestings(result, rsu_vestings_overlap, fa_vestings_overlap, overlap_start, overlap_end)
            
            # Compare sale events in overlap period
            self._compare_overlap_sales(result, rsu_sales_overlap, fa_sales_overlap, overlap_start, overlap_end)
            
        except ValueError:
            result.add_error("Date Range", f"Invalid overlap year format: {overlap_year}")
    
    def _compare_overlap_vestings(
        self,
        result: ValidationResult, 
        rsu_vestings: List[VestingEvent],
        fa_vestings: List[VestWiseDetails],
        start_date: date,
        end_date: date
    ):
        """Compare vesting events in overlapping period."""
        
        # Group by grant and date for comparison
        rsu_by_key = {}
        for vest in rsu_vestings:
            key = f"{vest.grant_number}_{vest.vest_date}"
            rsu_by_key[key] = vest
            
        fa_by_key = {}
        for vest in fa_vestings:
            key = f"{vest.grant_number}_{vest.vest_date}"
            fa_by_key[key] = vest
        
        all_keys = set(rsu_by_key.keys()) | set(fa_by_key.keys())
        
        for key in all_keys:
            rsu_vest = rsu_by_key.get(key)
            fa_vest = fa_by_key.get(key)
            
            if not rsu_vest:
                result.add_warning(
                    "Cross-Calculation",
                    f"Vesting event missing from RSU calculation but found in FA calculation",
                    expected=f"RSU vesting entry for {key}",
                    actual="Missing from RSU calculation",
                    context={
                        "overlap_period": f"{start_date} to {end_date}",
                        "missing_from": "RSU calculation (Financial Year)",
                        "present_in": "FA calculation (Calendar Year)",
                        "fa_calculation_data": {
                            "closing_shares": fa_vest.closing_shares,
                            "shares_sold": fa_vest.shares_sold,
                            "vest_date": str(fa_vest.vest_date),
                            "grant_number": fa_vest.grant_number
                        },
                        "recommendation": f"Check RSU calculation for vesting {fa_vest.vest_date} - may indicate FY vs CY period differences"
                    }
                )
            elif not fa_vest:
                result.add_warning(
                    "Cross-Calculation", 
                    f"Vesting event missing from FA calculation but found in RSU calculation",
                    expected=f"FA vesting entry for {key}",
                    actual="Missing from FA calculation",
                    context={
                        "overlap_period": f"{start_date} to {end_date}",
                        "missing_from": "FA calculation (Calendar Year)",
                        "present_in": "RSU calculation (Financial Year)",
                        "rsu_calculation_data": {
                            "vested_quantity": rsu_vest.vested_quantity,
                            "vest_date": str(rsu_vest.vest_date),
                            "grant_number": rsu_vest.grant_number,
                            "taxable_gain_inr": rsu_vest.taxable_gain_inr
                        },
                        "recommendation": f"Check FA calculation for vesting {rsu_vest.vest_date} - may indicate CY vs FY period differences"
                    }
                )
            else:
                # Gross vesting is taxable salary income, but only released
                # shares become a foreign asset. Validate both quantities.
                fa_gross_shares = getattr(
                    fa_vest, "gross_vested_shares", fa_vest.initial_shares
                )
                if not self._values_match(
                    rsu_vest.vested_quantity, fa_gross_shares
                ):
                    result.add_error(
                        "Cross-Calculation",
                        "Gross vesting quantity mismatch between RSU and FA calculations",
                        expected=f"{rsu_vest.vested_quantity} shares (RSU calculation)",
                        actual=f"{fa_gross_shares} shares (FA gross vesting)",
                        context={
                            "overlap_period": f"{start_date} to {end_date}",
                            "grant_number": rsu_vest.grant_number,
                            "vest_date": str(rsu_vest.vest_date),
                            "rsu_calculation": {
                                "total_vested": rsu_vest.vested_quantity,
                                "taxable_gain_inr": rsu_vest.taxable_gain_inr
                            },
                            "fa_calculation": {
                                "gross_vested_shares": fa_gross_shares,
                                "withheld_shares": getattr(fa_vest, "withheld_shares", 0.0),
                            },
                            "discrepancy_analysis": f"Difference of {abs(float(rsu_vest.vested_quantity) - float(fa_gross_shares))} shares",
                            "recommendation": f"Verify share calculations for grant {rsu_vest.grant_number} - check for data inconsistencies between RSU and FA data sources"
                        }
                    )

                expected_released = getattr(
                    rsu_vest, "released_quantity", rsu_vest.vested_quantity
                )
                fa_released_shares = fa_vest.closing_shares + fa_vest.shares_sold
                if not self._values_match(expected_released, fa_released_shares):
                    result.add_error(
                        "Cross-Calculation",
                        "Released-share quantity mismatch between RSU and FA calculations",
                        expected=f"{expected_released} shares (gross vesting less withholding)",
                        actual=(
                            f"{fa_released_shares} shares (FA calculation: "
                            f"{fa_vest.closing_shares} held + {fa_vest.shares_sold} sold)"
                        ),
                        context={
                            "overlap_period": f"{start_date} to {end_date}",
                            "grant_number": rsu_vest.grant_number,
                            "vest_date": str(rsu_vest.vest_date),
                            "gross_vested_shares": rsu_vest.vested_quantity,
                            "withheld_shares": getattr(rsu_vest, "withheld_quantity", 0.0),
                            "recommendation": "Match G&L sales by grant number and acquisition date",
                        },
                    )
    
    def _compare_overlap_sales(
        self,
        result: ValidationResult,
        rsu_sales: List[SaleEvent], 
        fa_sales: List[VestWiseDetails],
        start_date: date,
        end_date: date
    ):
        """Compare sale events in overlapping period."""
        
        self.logger.info(f"Comparing sale transactions in overlap period {start_date} to {end_date}")
        self.logger.info(f"RSU sales in overlap: {len(rsu_sales)} transactions")
        self.logger.info(f"FA vest-wise records with sales in overlap: {len([v for v in fa_sales if v.shares_sold > 0])}")
        
        # Group RSU sales by grant number and sale date for detailed comparison
        rsu_sales_by_grant_date = {}
        for sale in rsu_sales:
            # Create a unique key for each sale transaction
            key = f"{sale.grant_number}_{sale.sale_date}"
            if key in rsu_sales_by_grant_date:
                # Handle multiple sales on same date/grant by aggregating
                rsu_sales_by_grant_date[key]["shares_sold"] += sale.shares_sold
                rsu_sales_by_grant_date[key]["proceeds_inr"] += sale.sale_proceeds_inr
                rsu_sales_by_grant_date[key]["transaction_count"] += 1
            else:
                rsu_sales_by_grant_date[key] = {
                    "grant_number": sale.grant_number,
                    "sale_date": sale.sale_date,
                    "shares_sold": sale.shares_sold,
                    "proceeds_inr": sale.sale_proceeds_inr,
                    "transaction_count": 1
                }
        
        # Group FA sales by grant number (from vest_wise_details that have shares_sold > 0)
        fa_sales_by_grant = {}
        for vest in fa_sales:
            if vest.shares_sold > 0:
                grant = vest.grant_number
                if grant in fa_sales_by_grant:
                    # Multiple vest entries for same grant - aggregate sold shares
                    fa_sales_by_grant[grant]["shares_sold"] += vest.shares_sold  
                    fa_sales_by_grant[grant]["proceeds_inr"] += vest.gross_proceeds_inr
                    fa_sales_by_grant[grant]["vest_count"] += 1
                else:
                    fa_sales_by_grant[grant] = {
                        "grant_number": grant,
                        "vest_date": vest.vest_date,
                        "shares_sold": vest.shares_sold,
                        "proceeds_inr": vest.gross_proceeds_inr,
                        "vest_count": 1
                    }
        
        # Transaction-level validation: Check each RSU sale against FA data
        rsu_sale_transactions = len(rsu_sales_by_grant_date)
        fa_grants_with_sales = len(fa_sales_by_grant)
        matched_transactions = 0
        
        for rsu_key, rsu_sale in rsu_sales_by_grant_date.items():
            grant_number = rsu_sale["grant_number"]
            
            # Check if FA has sales for this grant
            if grant_number in fa_sales_by_grant:
                fa_sale = fa_sales_by_grant[grant_number]
                matched_transactions += 1
                
                # Compare share quantities
                if not self._values_match(rsu_sale["shares_sold"], fa_sale["shares_sold"], tolerance=0.1):
                    result.add_error(
                        "Cross-Calculation",
                        f"Share quantity mismatch for sold shares in overlap period",
                        expected=f"{rsu_sale['shares_sold']} shares (RSU calculation)",
                        actual=f"{fa_sale['shares_sold']} shares (FA calculation)",
                        context={
                            "overlap_period": f"{start_date} to {end_date}",
                            "grant_number": grant_number,
                            "rsu_sale_date": str(rsu_sale["sale_date"]),
                            "fa_vest_date": str(fa_sale["vest_date"]),
                            "missing_from": "FA calculation may not have complete sale data",
                            "present_in": "RSU calculation from G&L statements",
                            "rsu_transaction_details": {
                                "shares_sold": rsu_sale["shares_sold"],
                                "proceeds_inr": rsu_sale["proceeds_inr"],
                                "transaction_count": rsu_sale["transaction_count"]
                            },
                            "fa_transaction_details": {
                                "shares_sold": fa_sale["shares_sold"],
                                "proceeds_inr": fa_sale["proceeds_inr"], 
                                "vest_count": fa_sale["vest_count"]
                            },
                            "discrepancy_analysis": f"Difference of {abs(rsu_sale['shares_sold'] - fa_sale['shares_sold']):.2f} shares for grant {grant_number}",
                            "recommendation": f"Verify that FA calculation includes all sales for grant {grant_number} in the overlap period"
                        }
                    )
                
                # Compare proceeds (allow more tolerance for proceeds due to different calculation methods)
                if not self._values_match(rsu_sale["proceeds_inr"], fa_sale["proceeds_inr"], tolerance=1000):
                    result.add_warning(
                        "Cross-Calculation", 
                        f"Sale proceeds mismatch for grant in overlap period",
                        expected=f"₹{rsu_sale['proceeds_inr']:,.2f} (RSU calculation)",
                        actual=f"₹{fa_sale['proceeds_inr']:,.2f} (FA calculation)",
                        context={
                            "overlap_period": f"{start_date} to {end_date}",
                            "grant_number": grant_number,
                            "proceeds_difference": f"₹{abs(rsu_sale['proceeds_inr'] - fa_sale['proceeds_inr']):,.2f}",
                            "recommendation": "Minor proceeds differences may be due to different calculation methods or exchange rates"
                        }
                    )
            else:
                # RSU has a sale but FA doesn't show this grant as having sales
                result.add_error(
                    "Cross-Calculation",
                    f"Sale transaction found in RSU but missing from FA calculation",
                    expected=f"Sale record for grant {grant_number} with {rsu_sale['shares_sold']} shares",
                    actual="No sale record in FA calculation",
                    context={
                        "overlap_period": f"{start_date} to {end_date}",
                        "grant_number": grant_number,
                        "missing_from": "FA calculation (Calendar Year)",
                        "present_in": "RSU calculation (Financial Year)",
                        "rsu_sale_details": {
                            "sale_date": str(rsu_sale["sale_date"]),
                            "shares_sold": rsu_sale["shares_sold"],
                            "proceeds_inr": rsu_sale["proceeds_inr"]
                        },
                        "discrepancy_analysis": f"Grant {grant_number} sold {rsu_sale['shares_sold']} shares in RSU calculation but shows 0 sales in FA",
                        "recommendation": f"Check FA data sources for missing sale transaction on {rsu_sale['sale_date']}"
                    }
                )
        
        # Check for FA sales that don't have corresponding RSU sales
        for grant_number, fa_sale in fa_sales_by_grant.items():
            # Look for this grant in RSU sales
            rsu_has_sale = any(rsu["grant_number"] == grant_number for rsu in rsu_sales_by_grant_date.values())
            
            if not rsu_has_sale:
                result.add_error(
                    "Cross-Calculation",
                    f"Sale transaction found in FA but missing from RSU calculation",
                    expected=f"Sale record for grant {grant_number} with {fa_sale['shares_sold']} shares",
                    actual="No sale record in RSU calculation",
                    context={
                        "overlap_period": f"{start_date} to {end_date}",
                        "grant_number": grant_number,
                        "missing_from": "RSU calculation (Financial Year)",
                        "present_in": "FA calculation (Calendar Year)", 
                        "fa_sale_details": {
                            "vest_date": str(fa_sale["vest_date"]),
                            "shares_sold": fa_sale["shares_sold"],
                            "proceeds_inr": fa_sale["proceeds_inr"]
                        },
                        "discrepancy_analysis": f"Grant {grant_number} shows {fa_sale['shares_sold']} shares sold in FA but no sales in RSU",
                        "recommendation": f"Check RSU data sources (G&L statements) for missing sale transaction"
                    }
                )
        
        # Summary validation info
        total_rsu_sold = sum(sale.shares_sold for sale in rsu_sales)
        total_fa_sold = sum(vest.shares_sold for vest in fa_sales if vest.shares_sold > 0)
        
        self.logger.info(f"Transaction matching summary:")
        self.logger.info(f"  • RSU sale transactions: {rsu_sale_transactions}")
        self.logger.info(f"  • FA grants with sales: {fa_grants_with_sales}")
        self.logger.info(f"  • Matched transactions: {matched_transactions}")
        self.logger.info(f"  • Total RSU shares sold: {total_rsu_sold}")
        self.logger.info(f"  • Total FA shares sold: {total_fa_sold}")
        
        # Overall totals validation (as a final check)
        if not self._values_match(total_rsu_sold, total_fa_sold, tolerance=1.0):
            result.add_error(
                "Cross-Calculation",
                f"Total shares sold mismatch in overlap period",
                expected=f"{total_rsu_sold} shares (RSU calculation)",
                actual=f"{total_fa_sold} shares (FA calculation)",
                context={
                    "overlap_period": f"{start_date} to {end_date}",
                    "matched_transactions": f"{matched_transactions} out of {max(rsu_sale_transactions, fa_grants_with_sales)}",
                    "discrepancy_analysis": f"Aggregate difference of {abs(total_rsu_sold - total_fa_sold):.2f} shares",
                    "recommendation": "Review individual transaction mismatches above for specific discrepancies"
                }
            )
    
    def _validate_rsu_internal_consistency(self, result: ValidationResult, rsu_data: Dict[str, Any], financial_year: str = None):
        """Validate internal consistency within RSU calculations."""
        self.logger.info("Validating RSU internal consistency...")
        
        if "summary" in rsu_data:
            summary = rsu_data["summary"]
            
            # Validate summary totals against detail records
            if "vesting_events" in rsu_data:
                all_vesting_events = rsu_data["vesting_events"]
                
                # Filter vesting events by financial year if specified
                if financial_year:
                    vesting_events = self._filter_events_by_fy(all_vesting_events, financial_year)
                    self.logger.info(f"RSU internal validation: Filtered {len(vesting_events)} vesting events for {financial_year} from {len(all_vesting_events)} total events")
                    
                    # Debug: Show sample event dates for troubleshooting
                    if len(vesting_events) == 0 and len(all_vesting_events) > 0:
                        sample_dates = []
                        for i, event in enumerate(all_vesting_events[:3]):
                            date_str = getattr(event, 'vest_date', None) or getattr(event, 'date', None)
                            sample_dates.append(f"Event {i+1}: {date_str}")
                        self.logger.warning(f"No events matched {financial_year} filter. Sample event dates: {sample_dates}")
                else:
                    vesting_events = all_vesting_events
                    
                calculated_vesting_income = sum(v.taxable_gain_inr for v in vesting_events)
                summary_vesting_income = getattr(summary, "total_taxable_gain_inr", 0)
                
                if not self._values_match(calculated_vesting_income, summary_vesting_income):
                    result.add_error(
                        "Internal Consistency",
                        "RSU vesting income calculation mismatch between summary and detail records",
                        expected=f"₹{calculated_vesting_income:,.2f} (sum of {len(vesting_events)} vesting events)",
                        actual=f"₹{summary_vesting_income:,.2f} (summary total)",
                        context={
                            "calculation_source": "Individual vesting events taxable gain sum",
                            "summary_source": "RSU calculation summary",
                            "vesting_events_count": len(vesting_events),
                            "individual_vesting_amounts": [
                                {
                                    "vest_date": str(v.vest_date),
                                    "grant": v.grant_number,
                                    "taxable_gain_inr": v.taxable_gain_inr
                                } for v in vesting_events  # Show all vesting events
                            ],
                            "discrepancy_amount": f"₹{abs(calculated_vesting_income - summary_vesting_income):,.2f}",
                            "recommendation": "Check RSU calculation logic - may indicate aggregation error in summary calculation"
                        }
                    )
            
            # Only validate capital gains if there are actual sale events to compare
            if "sale_events" in rsu_data and rsu_data["sale_events"]:
                all_sale_events = rsu_data["sale_events"]
                
                # Filter sale events by financial year if specified
                if financial_year:
                    sale_events = self._filter_events_by_fy(all_sale_events, financial_year)
                    self.logger.info(f"RSU internal validation: Filtered {len(sale_events)} sale events for {financial_year} from {len(all_sale_events)} total events")
                else:
                    sale_events = all_sale_events
                    
                calculated_capital_gains = sum(s.capital_gain_inr for s in sale_events)
                summary_capital_gains = getattr(summary, "total_capital_gains_inr", 0)
                
                self.logger.info(f"RSU internal validation: Found {len(sale_events)} sale events, calculated gains: ₹{calculated_capital_gains:,.2f}, summary gains: ₹{summary_capital_gains:,.2f}")
                
                # Only validate if both have actual values (avoid false positives from date range filtering)
                if calculated_capital_gains != 0 or summary_capital_gains != 0:
                    if not self._values_match(calculated_capital_gains, summary_capital_gains):
                        result.add_error(
                            "Calculation Consistency", 
                            "Capital gains calculation mismatch between individual sales and summary",
                            expected=f"₹{calculated_capital_gains:,.2f} (sum of {len(sale_events)} sale transactions)",
                            actual=f"₹{summary_capital_gains:,.2f} (summary total)",
                            context={
                                "calculation_source": "Individual sale events capital gain sum",
                                "summary_source": "RSU calculation summary",
                                "sale_events_count": len(sale_events),
                                "individual_sale_amounts": [
                                    {
                                        "sale_date": str(s.sale_date),
                                        "grant": s.grant_number,
                                        "capital_gain_inr": s.capital_gain_inr,
                                        "gain_type": s.gain_type
                                    } for s in sale_events  # Show all sale events
                                ],
                                "discrepancy_amount": f"₹{abs(calculated_capital_gains - summary_capital_gains):,.2f}",
                                "recommendation": "Check RSU capital gains calculation logic - may indicate aggregation error or date filtering differences between detail records and summary calculation"
                            }
                        )
            else:
                # Note: Capital gains validation skipped - no sales occurred in this period
                self.logger.info("RSU internal validation: No sale events found for validation period - capital gains validation skipped")
    
    def _validate_fa_internal_consistency(self, result: ValidationResult, fa_data: Dict[str, Any]):
        """Validate internal consistency within FA calculations."""
        self.logger.info("Validating FA internal consistency...")
        
        if "summary" in fa_data and "vest_wise_details" in fa_data:
            summary = fa_data["summary"]
            vest_details = fa_data["vest_wise_details"]
            
            # Validate that sum of vest-wise details matches summary
            calculated_closing_value = sum(v.closing_value_inr for v in vest_details)
            summary_closing_value = getattr(summary, "closing_balance_inr", 0)
            
            if not self._values_match(calculated_closing_value, summary_closing_value):
                result.add_error(
                    "Internal Consistency",
                    "FA closing balance calculation mismatch between summary and vest-wise details",
                    expected=f"₹{calculated_closing_value:,.2f} (sum of {len(vest_details)} vest-wise details)",
                    actual=f"₹{summary_closing_value:,.2f} (FA summary)",
                    context={
                        "calculation_source": "Individual vest-wise details closing value sum",
                        "summary_source": "FA declaration summary",
                        "vest_details_count": len(vest_details),
                        "individual_vest_values": [
                            {
                                "vest_date": str(v.vest_date),
                                "grant": v.grant_number,
                                "closing_value_inr": v.closing_value_inr,
                                "closing_shares": v.closing_shares
                            } for v in vest_details  # Show all vest details
                        ],
                        "discrepancy_amount": f"₹{abs(calculated_closing_value - summary_closing_value):,.2f}",
                        "recommendation": "Check FA calculation logic - may indicate aggregation error or missing vest-wise details"
                    }
                )
            
            # Validate shares sold totals
            calculated_shares_sold = sum(v.shares_sold for v in vest_details)
            calculated_sale_proceeds = sum(v.gross_proceeds_inr for v in vest_details if v.gross_proceeds_inr > 0)
            
            if "equity_holdings" in fa_data:
                equity_holdings = fa_data["equity_holdings"]
                total_current_shares = sum(h.quantity for h in equity_holdings)
                
                # Cross-check: total vested - total sold should equal current holdings
                total_vested = sum(v.closing_shares + v.shares_sold for v in vest_details)
                expected_current = total_vested - calculated_shares_sold
                
                if not self._values_match(expected_current, total_current_shares, tolerance=1.0):
                    result.add_warning(
                        "Internal Consistency",
                        "FA current holdings calculation mismatch",
                        expected=f"{expected_current} shares",
                        actual=f"{total_current_shares} shares"
                    )
    
    def _values_match(self, val1: Any, val2: Any, tolerance: float = None) -> bool:
        """Check if two values match within tolerance."""
        if tolerance is None:
            tolerance = self.tolerance
            
        if val1 is None or val2 is None:
            return val1 == val2
        
        # Convert to float for comparison
        try:
            f1 = float(val1)
            f2 = float(val2)
            
            if f1 == 0 and f2 == 0:
                return True
            
            # Calculate percentage difference
            diff = abs(f1 - f2)
            avg = (abs(f1) + abs(f2)) / 2
            
            if avg == 0:
                return diff == 0
            
            return (diff / avg) <= tolerance
            
        except (ValueError, TypeError):
            return str(val1) == str(val2)
    
    def generate_validation_report(self, validation_result: ValidationResult) -> str:
        """Generate a detailed validation report."""
        
        lines = []
        lines.append("=" * 80)
        lines.append("🔍 COMPREHENSIVE VALIDATION REPORT")  
        lines.append("=" * 80)
        lines.append("")
        
        # Summary
        lines.append("📊 VALIDATION SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Overall Status: {'✅ PASSED' if validation_result.is_valid else '❌ FAILED'}")
        lines.append(f"Total Errors: {validation_result.get_error_count()}")
        lines.append(f"Total Warnings: {validation_result.get_warning_count()}")
        lines.append("")
        
        # Errors
        if validation_result.errors:
            lines.append("🚨 VALIDATION ERRORS")
            lines.append("-" * 40)
            for i, error in enumerate(validation_result.errors, 1):
                lines.append(f"{i}. {error}")
                if error.context:
                    lines.append("")
                    self._format_context_details(lines, error.context, "   ")
                lines.append("")
        
        # Warnings  
        if validation_result.warnings:
            lines.append("⚠️  VALIDATION WARNINGS")
            lines.append("-" * 40)
            for i, warning in enumerate(validation_result.warnings, 1):
                lines.append(f"{i}. {warning}")
                if warning.context:
                    lines.append("")
                    self._format_context_details(lines, warning.context, "   ")
                lines.append("")
        
        # Recommendations
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 40)
        if validation_result.get_error_count() > 0:
            lines.append("• Review data sources for consistency")
            lines.append("• Check calculation logic for discrepancies")
            lines.append("• Verify date ranges and financial year calculations")
        
        if validation_result.get_warning_count() > 0:
            lines.append("• Warnings indicate potential data quality issues")
            lines.append("• Consider manual verification of flagged transactions")
        
        if validation_result.is_valid:
            lines.append("• Calculations appear consistent across data sources")
            lines.append("• Consider periodic re-validation as data changes")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _format_context_details(self, lines: List[str], context: Dict[str, Any], indent: str = "   "):
        """Format detailed context information for validation report."""
        
        # Priority order for displaying context items
        priority_keys = [
            "missing_from", "present_in", "grant_number", "vesting_date", "sale_date",
            "overlap_period", "transaction_key", "discrepancy_analysis", "recommendation"
        ]
        
        # Display priority items first
        displayed_keys = set()
        for key in priority_keys:
            if key in context:
                self._format_context_item(lines, key, context[key], indent)
                displayed_keys.add(key)
        
        # Then display remaining items
        for key, value in context.items():
            if key not in displayed_keys:
                self._format_context_item(lines, key, value, indent)
    
    def _format_context_item(self, lines: List[str], key: str, value: Any, indent: str):
        """Format individual context item with appropriate formatting."""
        
        if key == "recommendation":
            lines.append(f"{indent}💡 Recommendation: {value}")
        elif key == "missing_from":
            lines.append(f"{indent}❌ Missing from: {value}")
        elif key == "present_in":
            lines.append(f"{indent}✅ Present in: {value}")
        elif key == "discrepancy_analysis":
            lines.append(f"{indent}📊 Analysis: {value}")
        elif key in ["grant_number", "vesting_date", "sale_date", "transaction_key"]:
            lines.append(f"{indent}🔍 {key.replace('_', ' ').title()}: {value}")
        elif key == "overlap_period":
            lines.append(f"{indent}📅 Overlap Period: {value}")
        elif isinstance(value, dict):
            lines.append(f"{indent}📋 {key.replace('_', ' ').title()}:")
            for sub_key, sub_value in value.items():
                lines.append(f"{indent}  • {sub_key}: {sub_value}")
        elif isinstance(value, list):
            lines.append(f"{indent}📝 {key.replace('_', ' ').title()}:")
            for i, item in enumerate(value):  # Show all items
                if isinstance(item, dict):
                    lines.append(f"{indent}  {i+1}. {item}")
                else:
                    lines.append(f"{indent}  {i+1}. {item}")
        else:
            lines.append(f"{indent}• {key.replace('_', ' ').title()}: {value}")
    
    def _filter_events_by_fy(self, events, financial_year: str):
        """Filter events to match the specified financial year (e.g., 'FY24-25')."""
        if not financial_year or not events:
            return events
            
        try:
            # Parse financial year (e.g., 'FY24-25' -> start=2024-04-01, end=2025-03-31)
            if financial_year.startswith("FY") and "-" in financial_year:
                year_parts = financial_year[2:].split("-")  # "24-25" -> ["24", "25"]
                start_year = 2000 + int(year_parts[0])  # 2024
                end_year = 2000 + int(year_parts[1])    # 2025
                
                from datetime import date
                fy_start = date(start_year, 4, 1)      # 2024-04-01
                fy_end = date(end_year, 3, 31)         # 2025-03-31
                
                # Filter events that fall within the financial year
                filtered_events = []
                
                for event in events:
                    event_date = None
                    
                    # Get date from event (handle both sale_date and vest_date)
                    if hasattr(event, 'sale_date') and event.sale_date:
                        event_date = event.sale_date
                    elif hasattr(event, 'vest_date') and event.vest_date:
                        event_date = event.vest_date
                    elif hasattr(event, 'date') and event.date:
                        event_date = event.date
                    
                    # Convert to date if it's a string
                    if isinstance(event_date, str):
                        try:
                            from datetime import datetime
                            event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                        except:
                            continue
                    
                    # Check if event falls within FY
                    if event_date and fy_start <= event_date <= fy_end:
                        filtered_events.append(event)
                return filtered_events
        except Exception as e:
            self.logger.warning(f"Failed to filter events by FY {financial_year}: {e}")
            
        return events
