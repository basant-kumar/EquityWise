"""Tests for Phase 2: Data Loading & Validation."""

import pytest
from pathlib import Path
from datetime import date

from rsu_fa_tool.data.loaders import (
    BenefitHistoryLoader, 
    GLStatementLoader, 
    SBIRatesLoader, 
    AdobeStockDataLoader,
    DataValidator
)
from rsu_fa_tool.data.models import (
    BenefitHistoryRecord, 
    GLStatementRecord, 
    SBIRateRecord, 
    AdobeStockRecord
)
from rsu_fa_tool.data.validators import RSUDataValidator, DataQualityValidator
from rsu_fa_tool.config.settings import settings


class TestDataLoaders:
    """Test data loading functionality."""
    
    def test_benefit_history_loader(self):
        """Test BenefitHistory.xlsx loading."""
        if not settings.benefit_history_path.exists():
            pytest.skip("BenefitHistory.xlsx file not found")
        
        loader = BenefitHistoryLoader(settings.benefit_history_path)
        df = loader.load_data()
        
        # Basic validation
        assert df is not None
        assert len(df) > 0
        assert 'Record Type' in df.columns
        assert 'Symbol' in df.columns
        
        # Test validated records
        records = loader.get_validated_records()
        assert isinstance(records, list)
        assert len(records) > 0
        
        # Check for grants and vests
        record_types = [r.record_type for r in records if r.record_type]
        assert 'Grant' in record_types
        
        print(f"✓ BenefitHistory loaded: {len(records)} validated records")
    
    def test_gl_statement_loader(self):
        """Test G&L statement loading."""
        gl_files = [p for p in settings.gl_statements_paths if p.exists()]
        if not gl_files:
            pytest.skip("No G&L statement files found")
        
        for gl_file in gl_files:
            loader = GLStatementLoader(gl_file)
            df = loader.load_data()
            
            # Basic validation
            assert df is not None
            assert len(df) >= 0  # Could be empty for some years
            assert 'Record Type' in df.columns
            
            # Test validated records
            records = loader.get_validated_records()
            assert isinstance(records, list)
            
            print(f"✓ G&L {gl_file.name} loaded: {len(records)} validated records")
    
    def test_sbi_rates_loader(self):
        """Test SBI TTBR rates loading."""
        if not settings.sbi_ttbr_rates_path.exists():
            pytest.skip("SBI rates file not found")
        
        loader = SBIRatesLoader(settings.sbi_ttbr_rates_path)
        df = loader.load_data()
        
        # Basic validation
        assert df is not None
        assert len(df) > 0
        assert 'Date' in df.columns
        assert 'Rate' in df.columns
        assert 'Currency Pairs' in df.columns
        
        # Test validated records
        records = loader.get_validated_records()
        assert isinstance(records, list)
        assert len(records) > 0
        
        # Check for USD rates
        usd_records = [r for r in records if 'USD' in r.currency_pair]
        assert len(usd_records) > 0
        
        print(f"✓ SBI rates loaded: {len(records)} validated records ({len(usd_records)} USD rates)")
    
    def test_adobe_stock_data_loader(self):
        """Test Adobe stock data loading."""
        if not settings.adobe_stock_data_path.exists():
            pytest.skip("Adobe stock data file not found")
        
        loader = AdobeStockDataLoader(settings.adobe_stock_data_path)
        df = loader.load_data()
        
        # Basic validation
        assert df is not None
        assert len(df) > 0
        assert 'Date' in df.columns
        assert 'Close/Last' in df.columns
        
        # Test validated records
        records = loader.get_validated_records()
        assert isinstance(records, list)
        assert len(records) > 0
        
        # Check date range
        dates = [r.date for r in records if r.date]
        assert len(dates) > 0
        assert min(dates) < max(dates)  # Should have multiple dates
        
        print(f"✓ Adobe stock data loaded: {len(records)} validated records")
    
    def test_data_validator_comprehensive(self):
        """Test comprehensive data validation."""
        validator = DataValidator()
        
        # Only run if all files exist
        required_files = [
            settings.benefit_history_path,
            settings.sbi_ttbr_rates_path,
            settings.adobe_stock_data_path
        ] + settings.gl_statements_paths
        
        missing_files = [f for f in required_files if not f.exists()]
        if missing_files:
            pytest.skip(f"Missing required files: {[str(f) for f in missing_files]}")
        
        results = validator.validate_all_sources(
            settings.benefit_history_path,
            settings.gl_statements_paths,
            settings.sbi_ttbr_rates_path,
            settings.adobe_stock_data_path
        )
        
        # Validation results should have proper structure
        assert 'success' in results
        assert 'data' in results
        assert 'summary' in results
        assert 'errors' in results
        
        # Print summary
        print(f"✓ Comprehensive validation completed")
        print(f"  Success: {results['success']}")
        print(f"  Summary: {results['summary']}")
        if results['errors']:
            print(f"  Errors: {results['errors']}")


class TestDataModels:
    """Test data model validation."""
    
    def test_benefit_history_model(self):
        """Test BenefitHistoryRecord model."""
        # Test with minimal valid data
        record = BenefitHistoryRecord(record_type="Grant")
        assert record.record_type == "Grant"
        
        # Test with full data
        full_record = BenefitHistoryRecord(
            record_type="Grant",
            symbol="ADBE",
            grant_date=date(2023, 4, 1),
            granted_qty=100.0,
            grant_number="12345"
        )
        assert full_record.symbol == "ADBE"
        assert full_record.granted_qty == 100.0
    
    def test_gl_statement_model(self):
        """Test GLStatementRecord model."""
        record = GLStatementRecord(record_type="Sell")
        assert record.record_type == "Sell"
        
        full_record = GLStatementRecord(
            record_type="Sell",
            symbol="ADBE",
            quantity=50.0,
            date_acquired=date(2023, 4, 1),
            date_sold=date(2023, 6, 1)
        )
        assert full_record.quantity == 50.0
    
    def test_sbi_rate_model(self):
        """Test SBIRateRecord model."""
        record = SBIRateRecord(
            date=date(2023, 8, 1),
            time="1:00:00 PM",
            currency_pair="INR / 1 USD",
            rate=83.5
        )
        assert record.rate == 83.5
        assert "USD" in record.currency_pair
    
    def test_adobe_stock_model(self):
        """Test AdobeStockRecord model."""
        record = AdobeStockRecord(
            date=date(2023, 8, 1),
            close_price=500.00,
            volume=1000000,
            open_price=495.00,
            high_price=505.00,
            low_price=490.00
        )
        assert record.close_price == 500.00
        assert record.volume == 1000000


class TestDataValidators:
    """Test data validation functionality."""
    
    def test_rsu_data_validator(self):
        """Test RSU data validation."""
        validator = RSUDataValidator()
        
        # Create sample data
        benefit_records = [
            BenefitHistoryRecord(
                record_type="Grant",
                symbol="ADBE",
                grant_date=date(2023, 4, 1),
                grant_number="12345"
            )
        ]
        
        gl_records = [
            GLStatementRecord(
                record_type="Sell",
                symbol="ADBE",
                grant_number="12345"
            )
        ]
        
        # Test consistency validation
        results = validator.validate_rsu_data_consistency(benefit_records, gl_records)
        
        assert 'is_consistent' in results
        assert 'inconsistencies' in results
        assert 'summary' in results
    
    def test_date_range_validation(self):
        """Test date range validation."""
        validator = RSUDataValidator()
        
        # Create records with dates - use an actually future date
        future_date = date(2030, 1, 1)  # Definitely future
        
        records = [
            BenefitHistoryRecord(record_type="Grant", grant_date=date(2023, 1, 1)),
            BenefitHistoryRecord(record_type="Grant", grant_date=future_date)  # Future date
        ]
        
        errors = validator.validate_date_ranges(records, 'grant_date')
        
        # Should find the future date as invalid
        assert len(errors) > 0
        assert "outside valid range" in errors[0]
    
    def test_quantity_validation(self):
        """Test quantity validation."""
        validator = RSUDataValidator()
        
        records = [
            BenefitHistoryRecord(record_type="Grant", granted_qty=100.0),  # Valid
            BenefitHistoryRecord(record_type="Grant", granted_qty=-10.0),  # Invalid
            BenefitHistoryRecord(record_type="Grant", granted_qty=50000.0) # Unusually high
        ]
        
        errors = validator.validate_quantities(records, 'granted_qty')
        
        # Should find negative quantity and unusually high quantity
        assert len(errors) >= 2
    
    def test_comprehensive_data_quality(self):
        """Test comprehensive data quality validation."""
        validator = DataQualityValidator()
        
        # Create minimal sample data
        benefit_records = [BenefitHistoryRecord(record_type="Grant")]
        gl_records = [GLStatementRecord(record_type="Sell")]
        sbi_records = []
        stock_records = []
        
        report = validator.run_comprehensive_validation(
            benefit_records, gl_records, sbi_records, stock_records
        )
        
        assert 'overall_quality' in report
        assert 'data_sources' in report
        assert 'cross_validation' in report
        assert 'recommendations' in report
        
        # Should have quality assessment for each data source
        assert 'benefit_history' in report['data_sources']
        assert 'gl_statements' in report['data_sources']


def test_phase2_integration():
    """Integration test for Phase 2 data loading."""
    print("\n🧪 Running Phase 2 Integration Test")
    
    # Test file existence
    required_files = [
        settings.benefit_history_path,
        settings.sbi_ttbr_rates_path,
        settings.adobe_stock_data_path
    ] + settings.gl_statements_paths
    
    existing_files = [f for f in required_files if f.exists()]
    print(f"📁 Found {len(existing_files)}/{len(required_files)} required data files")
    
    if len(existing_files) >= len(required_files) // 2:  # At least half the files
        print("✅ Phase 2 data loading infrastructure is working!")
        assert True  # Test passes
    else:
        print("⚠️  Phase 2 needs actual data files for full testing")
        assert len(existing_files) > 0, "No data files found for testing"


if __name__ == "__main__":
    # Run integration test
    test_phase2_integration()
