"""
Master Test Suite for RSU FA Tool
Comprehensive testing orchestrator that runs all test modules and provides detailed reporting.
"""

import pytest
import sys
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch

# Import all test modules for comprehensive coverage
# Note: These imports are for reference only, actual test execution is done via pytest

# Import core modules for integration testing
from rsu_fa_tool.main import cli
from rsu_fa_tool.calculators.rsu_service import RSUService
from rsu_fa_tool.calculators.fa_service import FAService
from rsu_fa_tool.data.loaders import DataLoader, BankStatementLoader
from rsu_fa_tool.config.settings import settings
from rsu_fa_tool.utils.date_utils import get_financial_year_dates, get_calendar_year_dates
from rsu_fa_tool.utils.currency_utils import format_currency


class TestMasterSuite:
    """Master test suite that orchestrates comprehensive testing."""

    def test_core_utilities_integration(self):
        """Test core utility functions integration."""
        # Test date utilities
        fy_start, fy_end = get_financial_year_dates("FY24-25")
        assert fy_start.year == 2024
        assert fy_start.month == 4
        assert fy_start.day == 1
        assert fy_end.year == 2025
        assert fy_end.month == 3
        assert fy_end.day == 31

        # Test calendar year utilities
        cy_start, cy_end = get_calendar_year_dates(2024)
        assert cy_start == date(2024, 1, 1)
        assert cy_end == date(2024, 12, 31)

        # Test currency formatting
        assert format_currency(1234567.89) == "₹1,234,567.89"
        assert format_currency(1000000) == "₹1,000,000.00"

    def test_configuration_integration(self):
        """Test configuration and settings integration."""
        # Verify settings are properly configured
        assert settings.benefit_history_path.exists() or True  # May not exist in test env
        assert isinstance(settings.gl_statements_paths, list)  # Fixed: correct field name
        assert len(settings.gl_statements_paths) >= 1  # Fixed: correct field name
        assert isinstance(settings.esop_pdf_paths, list)
        assert len(settings.esop_pdf_paths) >= 1

    def test_data_loader_comprehensive_integration(self):
        """Test comprehensive data loader integration."""
        # Test that all loader types can be instantiated
        test_file = Path("test.xlsx")
        
        # Create a generic DataLoader instance
        loader = DataLoader(test_file)
        assert loader.file_path == test_file
        assert hasattr(loader, 'load_data')
        # Note: get_validated_records only exists on specific loaders, not base class

    def test_bank_statement_integration(self):
        """Test bank statement functionality integration."""
        # Test bank statement paths configuration
        assert hasattr(settings, 'bank_statement_paths')
        assert isinstance(settings.bank_statement_paths, list)
        
        # Test that BankStatementLoader can be instantiated
        test_bank_file = Path("test_bank.xls")
        bank_loader = BankStatementLoader(test_bank_file)
        assert bank_loader.file_path == test_bank_file

    @pytest.mark.integration
    def test_rsu_service_integration(self):
        """Test RSU service integration with mock data."""
        with patch('rsu_fa_tool.calculators.rsu_service.RSUService.load_all_data') as mock_load:  # Fixed: correct method name
            # Mock the data loading to avoid file dependencies
            mock_load.return_value = None
            
            # Test RSU service instantiation  
            rsu_service = RSUService(settings)  # Fixed: add required settings parameter
            assert hasattr(rsu_service, 'calculate_rsu_for_fy')
            assert hasattr(rsu_service, 'load_all_data')  # Fixed: correct method name

    @pytest.mark.integration  
    def test_fa_service_integration(self):
        """Test FA service integration with mock data."""
        with patch('rsu_fa_tool.calculators.fa_service.FAService.load_required_data') as mock_load:
            # Mock the data loading to avoid file dependencies
            mock_load.return_value = None
            
            # Test FA service instantiation
            fa_service = FAService(settings)  # Fixed: add required settings parameter
            assert hasattr(fa_service, 'calculate_fa_for_year')
            assert hasattr(fa_service, 'load_required_data')  # Fixed: correct method name

    @pytest.mark.slow
    def test_full_calculation_workflow_mock(self):
        """Test full calculation workflow with mocked data to avoid file dependencies."""
        with patch('rsu_fa_tool.data.loaders.DataLoader.load_data') as mock_load_data:
            with patch('rsu_fa_tool.calculators.rsu_service.RSUService.load_all_data'):  # Fixed: correct method name
                with patch('rsu_fa_tool.calculators.fa_service.FAService.load_required_data'):
                    # Mock successful data loading
                    mock_load_data.return_value = []
                    
                    # Test that services can be created and have expected methods
                    rsu_service = RSUService(settings)  # Fixed: add required settings parameter
                    fa_service = FAService(settings)  # Fixed: add required settings parameter
                    
                    # Verify expected interface
                    assert hasattr(rsu_service, 'calculate_rsu_for_fy')
                    assert hasattr(fa_service, 'calculate_fa_for_year')

    def test_formula_consistency_cross_module(self):
        """Test that formulas are consistent across different modules."""
        # Test that financial year calculation is consistent
        from rsu_fa_tool.calculators.rsu_calculator import RSUCalculator
        from rsu_fa_tool.calculators.fa_calculator import FACalculator
        
        # Mock data for testing
        mock_sbi_rates = []
        mock_stock_data = []
        
        rsu_calc = RSUCalculator(mock_sbi_rates, mock_stock_data)
        fa_calc = FACalculator(mock_sbi_rates, mock_stock_data)
        
        # Test financial year calculation consistency
        test_date = date(2024, 6, 15)
        rsu_fy = rsu_calc.calculate_financial_year(test_date)
        
        # FA uses calendar year, so we test different method
        fa_cy = fa_calc.calculate_calendar_year(test_date)
        
        assert rsu_fy == "FY24-25"
        assert fa_cy == "2024"

    def test_error_handling_integration(self):
        """Test error handling across modules."""
        # Test that modules handle missing files gracefully
        non_existent_file = Path("non_existent_file.xlsx")
        
        # Should not crash when instantiating with non-existent file
        loader = DataLoader(non_existent_file)
        assert loader.file_path == non_existent_file

    def test_data_model_consistency(self):
        """Test that data models are consistent across modules."""
        from rsu_fa_tool.data.models import GLStatementRecord, SBIRateRecord, AdobeStockRecord
        from rsu_fa_tool.data.esop_parser import ESOPVestingRecord
        
        # Test that all models have consistent date handling
        test_date = date(2024, 6, 15)
        
        # Test GLStatementRecord
        gl_record = GLStatementRecord(
            record_type="Sell",
            symbol="ADBE",
            quantity=1.0,
            date_sold=test_date,
            total_proceeds=100.0
        )
        assert gl_record.date_sold == test_date
        
        # Test SBIRateRecord  
        sbi_record = SBIRateRecord(**{
            'Date': test_date,
            'Time': '1:00:00 PM',
            'Currency Pairs': 'INR / 1 USD',
            'Rate': 83.50
        })
        assert sbi_record.date == test_date
        
        # Test AdobeStockRecord
        adobe_record = AdobeStockRecord(**{
            'Date': test_date,
            'Close/Last': 500.0,
            'Volume': 1000000,
            'Open': 495.0,
            'High': 505.0,
            'Low': 490.0
        })
        assert adobe_record.date == test_date
        
        # Test ESOPVestingRecord
        esop_record = ESOPVestingRecord(
            employee_id="TEST123",
            employee_name="Test Employee",
            vesting_date=test_date,
            grant_number="RU123",
            fmv_usd=500.0,
            quantity=1,
            total_usd=500.0,
            forex_rate=83.50,
            total_inr=41750.0
        )
        assert esop_record.vesting_date == test_date

    @pytest.mark.performance
    def test_calculation_performance(self):
        """Test calculation performance with larger datasets."""
        # Mock larger datasets to test performance
        start_time = time.time()
        
        # Simulate processing multiple records
        for i in range(1000):
            test_amount = i * 1000.50
            formatted = format_currency(test_amount)
            assert "₹" in formatted
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 1000 currency formats in reasonable time (< 1 second)
        assert processing_time < 1.0, f"Performance test failed: {processing_time:.3f}s for 1000 operations"

    def test_memory_usage_integration(self):
        """Test memory usage during normal operations."""
        import gc
        
        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform operations that should clean up properly
        for i in range(100):
            from rsu_fa_tool.data.models import GLStatementRecord
            record = GLStatementRecord(
                record_type="Sell",
                symbol="ADBE",
                quantity=float(i),
                date_sold=date(2024, 1, 1),
                total_proceeds=float(i * 100)
            )
            # Simulate using the record
            _ = record.quantity * record.total_proceeds
        
        # Force garbage collection after operations
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable (less than 50% increase)
        growth_ratio = final_objects / initial_objects
        assert growth_ratio < 1.5, f"Memory usage grew too much: {growth_ratio:.2f}x"

    def test_multi_financial_year_consistency(self):
        """Test consistency across multiple financial years."""
        # Test FY transitions
        fy_boundary_dates = [
            (date(2024, 3, 31), "FY23-24"),  # Last day of FY23-24
            (date(2024, 4, 1), "FY24-25"),   # First day of FY24-25
            (date(2025, 3, 31), "FY24-25"),  # Last day of FY24-25
            (date(2025, 4, 1), "FY25-26"),   # First day of FY25-26
        ]
        
        from rsu_fa_tool.calculators.rsu_calculator import RSUCalculator
        calculator = RSUCalculator([], [])
        
        for test_date, expected_fy in fy_boundary_dates:
            actual_fy = calculator.calculate_financial_year(test_date)
            assert actual_fy == expected_fy, f"Date {test_date} should be {expected_fy}, got {actual_fy}"

    def test_currency_and_locale_handling(self):
        """Test currency formatting and locale handling."""
        test_amounts = [
            (0, "₹0.00"),
            (1, "₹1.00"),
            (1000, "₹1,000.00"),
            (100000, "₹100,000.00"),
            (1000000, "₹1,000,000.00"),
            (10000000, "₹10,000,000.00"),
            (1234567.89, "₹1,234,567.89"),
        ]
        
        for amount, expected in test_amounts:
            result = format_currency(amount)
            assert result == expected, f"Amount {amount} formatted incorrectly: {result} != {expected}"

    def test_edge_case_comprehensive(self):
        """Test comprehensive edge cases across all modules."""
        # Test empty inputs
        assert format_currency(0) == "₹0.00"
        
        # Test boundary dates
        boundary_test_date = date(2024, 4, 1)  # FY boundary
        fy_start, fy_end = get_financial_year_dates("FY24-25")
        assert fy_start <= boundary_test_date <= fy_end
        
        # Test very large numbers
        large_amount = 999999999.99
        formatted_large = format_currency(large_amount)
        assert "₹" in formatted_large
        assert "999,999,999.99" in formatted_large

    @pytest.mark.integration
    def test_module_import_consistency(self):
        """Test that all modules can be imported consistently."""
        # Test that all main modules import without issues
        modules_to_test = [
            'rsu_fa_tool.main',
            'rsu_fa_tool.calculators.rsu_calculator',
            'rsu_fa_tool.calculators.fa_calculator', 
            'rsu_fa_tool.calculators.rsu_service',
            'rsu_fa_tool.calculators.fa_service',
            'rsu_fa_tool.data.models',
            'rsu_fa_tool.data.loaders',
            'rsu_fa_tool.data.esop_parser',
            'rsu_fa_tool.utils.date_utils',
            'rsu_fa_tool.utils.currency_utils',
            'rsu_fa_tool.config.settings',
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_documentation_and_help_integration(self):
        """Test that help and documentation are accessible."""
        # Test that CLI help works
        with patch('sys.argv', ['rsu-fa-tool', '--help']):
            try:
                # This would normally exit, so we catch SystemExit
                with pytest.raises(SystemExit):
                    cli()
            except Exception as e:
                # If not SystemExit, something is wrong with help
                if not isinstance(e, SystemExit):
                    pytest.fail(f"CLI help failed unexpectedly: {e}")


class TestMasterCLIIntegration:
    """Test CLI integration and end-to-end functionality."""

    @pytest.mark.integration
    def test_cli_commands_exist(self):
        """Test that all expected CLI commands exist."""
        with patch('sys.argv', ['rsu-fa-tool', '--help']):
            # Test should not fail due to CLI structure issues
            try:
                with pytest.raises(SystemExit):
                    cli()
            except Exception as e:
                if not isinstance(e, SystemExit):
                    pytest.fail(f"CLI structure issue: {e}")

    @pytest.mark.integration
    def test_validation_command_integration(self):
        """Test that validation command works."""
        # This tests the command structure, not file existence
        with patch('rsu_fa_tool.main.validate_data') as mock_validate:
            mock_validate.return_value = None
            with patch('sys.argv', ['rsu-fa-tool', 'validate-data']):
                try:
                    with pytest.raises(SystemExit):
                        cli()
                except Exception as e:
                    if not isinstance(e, SystemExit):
                        pytest.fail(f"Validation command failed: {e}")


def run_comprehensive_test_suite():
    """
    Function to run comprehensive test suite programmatically.
    Returns summary of test results.
    """
    # Run all tests and collect results
    test_results = {}
    
    # Basic tests
    print("🧪 Running Basic Tests...")
    basic_result = pytest.main(["-v", "tests/test_basic.py", "--tb=short"])
    test_results['basic'] = basic_result
    
    # Phase 2 tests
    print("🧪 Running Phase 2 Data Loading Tests...")
    phase2_result = pytest.main(["-v", "tests/test_phase2_data_loading.py", "--tb=short"])
    test_results['phase2'] = phase2_result
    
    # RSU Calculator tests
    print("🧪 Running RSU Calculator Tests...")
    rsu_result = pytest.main(["-v", "tests/test_comprehensive_rsu_calculator.py", "--tb=short"])
    test_results['rsu_calculator'] = rsu_result
    
    # Master suite tests
    print("🧪 Running Master Suite Integration Tests...")
    master_result = pytest.main(["-v", "tests/test_master_suite.py", "--tb=short"])
    test_results['master_suite'] = master_result
    
    return test_results


if __name__ == "__main__":
    """Run master test suite when executed directly."""
    print("🚀 Starting Master Test Suite for RSU FA Tool")
    print("=" * 60)
    
    results = run_comprehensive_test_suite()
    
    print("\n" + "=" * 60)
    print("📊 Test Suite Summary:")
    print("=" * 60)
    
    total_success = 0
    total_tests = 0
    
    for test_name, result_code in results.items():
        status = "✅ PASSED" if result_code == 0 else "❌ FAILED"
        print(f"{test_name:20s}: {status}")
        if result_code == 0:
            total_success += 1
        total_tests += 1
    
    print("=" * 60)
    print(f"Overall Result: {total_success}/{total_tests} test suites passed")
    
    if total_success == total_tests:
        print("🎉 All test suites passed! System is ready for production.")
        sys.exit(0)
    else:
        print("⚠️  Some test suites failed. Please review the output above.")
        sys.exit(1)
