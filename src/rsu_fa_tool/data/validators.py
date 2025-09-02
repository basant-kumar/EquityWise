"""Data validation utilities for RSU FA Tool."""

from datetime import date as Date, datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from .models import BenefitHistoryRecord, GLStatementRecord, RSUTransaction, ForeignAssetRecord
from .loaders import BenefitHistoryLoader, GLStatementLoader, SBIRatesLoader, AdobeStockDataLoader


class RSUDataValidator:
    """Validates RSU-related data integrity and consistency."""
    
    def __init__(self):
        """Initialize the RSU data validator."""
        self.validation_errors = []
        self.warnings = []
    
    def validate_rsu_data_consistency(
        self,
        benefit_records: List[BenefitHistoryRecord],
        gl_records: List[GLStatementRecord]
    ) -> Dict[str, Any]:
        """Validate consistency between BenefitHistory and G&L statement data.
        
        Args:
            benefit_records: List of validated benefit history records.
            gl_records: List of validated G&L statement records.
            
        Returns:
            Dictionary with validation results and inconsistencies found.
        """
        results = {
            'is_consistent': True,
            'inconsistencies': [],
            'summary': {
                'benefit_grants': 0,
                'benefit_vests': 0,
                'gl_transactions': 0,
                'matched_transactions': 0
            }
        }
        
        # Count benefit history events
        grants = [r for r in benefit_records if r.record_type == 'Grant']
        vests = [r for r in benefit_records if r.record_type == 'Event' and r.event_type == 'Vest']
        
        results['summary']['benefit_grants'] = len(grants)
        results['summary']['benefit_vests'] = len(vests)
        results['summary']['gl_transactions'] = len([r for r in gl_records if r.record_type == 'Sell'])
        
        # Cross-validate vesting records with G&L acquisition records
        for vest_record in vests:
            if not vest_record.vest_date or not vest_record.qty_or_amount:
                continue
                
            # Find matching G&L records by grant number and quantity
            matching_gl = [
                gl for gl in gl_records 
                if (gl.grant_number == vest_record.grant_number and 
                    gl.quantity and abs(gl.quantity - vest_record.qty_or_amount) < 0.01)
            ]
            
            if not matching_gl:
                results['inconsistencies'].append({
                    'type': 'missing_gl_record',
                    'vest_date': vest_record.vest_date,
                    'grant_number': vest_record.grant_number,
                    'quantity': vest_record.qty_or_amount
                })
            else:
                results['summary']['matched_transactions'] += 1
        
        if results['inconsistencies']:
            results['is_consistent'] = False
            
        logger.info(f"RSU data consistency check: {results['summary']['matched_transactions']} matched, "
                   f"{len(results['inconsistencies'])} inconsistencies")
        
        return results
    
    def validate_date_ranges(
        self,
        records: List[Any],
        date_field: str,
        min_date: Optional[Date] = None,
        max_date: Optional[Date] = None
    ) -> List[str]:
        """Validate that dates in records fall within expected ranges.
        
        Args:
            records: List of records to validate.
            date_field: Name of the date field to check.
            min_date: Minimum allowed date.
            max_date: Maximum allowed date.
            
        Returns:
            List of validation error messages.
        """
        errors = []
        
        if min_date is None:
            min_date = Date(2010, 1, 1)  # Reasonable minimum for RSU data
        if max_date is None:
            max_date = Date.today()
        
        for i, record in enumerate(records):
            record_date = getattr(record, date_field, None)
            if record_date and (record_date < min_date or record_date > max_date):
                errors.append(f"Record {i}: {date_field} {record_date} outside valid range "
                            f"({min_date} to {max_date})")
        
        return errors
    
    def validate_quantities(self, records: List[Any], quantity_field: str) -> List[str]:
        """Validate that quantities are positive and reasonable.
        
        Args:
            records: List of records to validate.
            quantity_field: Name of the quantity field to check.
            
        Returns:
            List of validation error messages.
        """
        errors = []
        
        for i, record in enumerate(records):
            quantity = getattr(record, quantity_field, None)
            if quantity is not None:
                if quantity <= 0:
                    errors.append(f"Record {i}: {quantity_field} must be positive, got {quantity}")
                elif quantity > 10000:  # Reasonable upper limit for RSU quantities
                    errors.append(f"Record {i}: {quantity_field} {quantity} seems unusually high")
        
        return errors


class ForeignAssetsValidator:
    """Validates Foreign Assets declaration data."""
    
    def validate_fa_completeness(
        self,
        stock_records: List[Any],
        calendar_year: int
    ) -> Dict[str, Any]:
        """Validate completeness of Foreign Assets data for a calendar year.
        
        Args:
            stock_records: List of stock holding records.
            calendar_year: Calendar year to validate.
            
        Returns:
            Dictionary with validation results.
        """
        results = {
            'is_complete': True,
            'missing_data': [],
            'year': calendar_year,
            'total_records': len(stock_records)
        }
        
        # Check for year-end data
        year_end_date = Date(calendar_year, 12, 31)
        year_end_records = [
            r for r in stock_records 
            if hasattr(r, 'date') and r.date == year_end_date
        ]
        
        if not year_end_records:
            results['is_complete'] = False
            results['missing_data'].append(f"No stock data for year-end {year_end_date}")
        
        return results


class DataQualityValidator:
    """Validates overall data quality across all sources."""
    
    def run_comprehensive_validation(
        self,
        benefit_records: List[BenefitHistoryRecord],
        gl_records: List[GLStatementRecord],
        sbi_records: List[Any],
        stock_records: List[Any]
    ) -> Dict[str, Any]:
        """Run comprehensive data quality validation across all sources.
        
        Args:
            benefit_records: Benefit history records.
            gl_records: G&L statement records.
            sbi_records: SBI rate records.
            stock_records: Adobe stock data records.
            
        Returns:
            Comprehensive validation report.
        """
        report = {
            'overall_quality': 'good',
            'data_sources': {
                'benefit_history': {'count': len(benefit_records), 'quality': 'good', 'issues': []},
                'gl_statements': {'count': len(gl_records), 'quality': 'good', 'issues': []},
                'sbi_rates': {'count': len(sbi_records), 'quality': 'good', 'issues': []},
                'stock_data': {'count': len(stock_records), 'quality': 'good', 'issues': []},
            },
            'cross_validation': {},
            'recommendations': []
        }
        
        # Validate individual data sources
        rsu_validator = RSUDataValidator()
        fa_validator = ForeignAssetsValidator()
        
        # Cross-validate RSU data
        consistency_check = rsu_validator.validate_rsu_data_consistency(benefit_records, gl_records)
        report['cross_validation']['rsu_consistency'] = consistency_check
        
        if not consistency_check['is_consistent']:
            report['overall_quality'] = 'fair'
            report['recommendations'].append("Review RSU data inconsistencies between BenefitHistory and G&L statements")
        
        # Check data coverage
        current_year = Date.today().year
        fa_completeness = fa_validator.validate_fa_completeness(stock_records, current_year - 1)
        report['cross_validation']['fa_completeness'] = fa_completeness
        
        if not fa_completeness['is_complete']:
            report['recommendations'].append("Ensure complete stock data for Foreign Assets calculations")
        
        logger.info(f"Comprehensive data quality validation completed. Overall quality: {report['overall_quality']}")
        
        return report
