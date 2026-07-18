# EquityWise Changelog

All notable changes to the EquityWise project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 🐛 Bug Fixes

- Deduct confirmed selling expenses that are absent from broker G&L statements
  when calculating capital gains under Section 48.
- Convert deductible USD sale expenses using each sale date's Rule 115 rate.
- Match bank remittances one-to-one with the nearest sale date and use exact
  bank credits, including line-level rounding, for cash reconciliation.
- Show gross G&L gain, deductible sale expense, and net capital gain separately
  in CLI, Excel, and CSV reports.

## [2.0.0] - 2025-09-07

### 🆕 Major New Features

#### Comprehensive Data Validation System
- **Added `--validate` flag** to both RSU and FA calculation commands
- **Cross-data source validation** between BenefitHistory, RSU PDFs, and G&L statements
- **Date range overlap analysis** for FY-based RSU vs CY-based FA calculations
- **Internal consistency validation** verifying summary totals match detailed transactions
- **Detailed error reporting** showing exactly which transactions are missing or inconsistent

#### Enhanced Excel Report Formatting
- **Professional currency formatting**: Uses proper Excel number formats (`₹#,##0.00`) instead of text strings
- **Dynamic column widths**: Prevents "######" display by implementing rule-based width calculation
- **Total rows**: Added automatic totals for USD and INR columns in all relevant sheets
- **Wrap text headers**: Enabled wrap text for better column header readability
- **Separated transaction details**: RSU reports now separate vesting and sold details clearly

### 🔧 Improvements

#### Data Processing Enhancements
- **Fixed BenefitHistory interpretation**: Correctly uses "Date" column for actual transaction dates
- **Improved event type handling**: Distinguishes between "Shares sold" (actual sales) and "Shares released" (vesting events)
- **Enhanced data consistency**: Unified data processing logic across RSU, FA, and validation systems
- **Future transaction filtering**: Excludes future-dated transactions from validation

#### User Experience Improvements
- **Excel temporary file handling**: Automatically filters out Excel lock files (`~$*.xlsx`) 
- **Enhanced error messages**: Provides specific details about missing/inconsistent transactions
- **Complete validation reports**: Removed truncation to show full transaction details
- **Better progress indicators**: Improved console output with detailed validation results

### 🐛 Bug Fixes

#### Critical Bug Fixes
- **Fixed "Shares released" misclassification**: Validation no longer treats vesting events as sales
- **Fixed capital gains validation**: Only validates capital gains when actual sales occurred
- **Fixed field name mismatch**: Corrected `total_vesting_income_inr` to `total_taxable_gain_inr`
- **Fixed financial year filtering**: Validation now properly filters events by FY to match summaries

#### Data Loading Fixes  
- **Excel temporary files**: Fixed "Excel file format cannot be determined" errors for `~$*.xlsx` files
- **Multiple transaction aggregation**: Fixed validation logic for multiple sales on same date/grant
- **Date range validation**: Improved handling of different date ranges and future transactions

### 📊 Enhanced Reporting

#### Excel Report Improvements
- **RSU Reports**: 
  - Separated vesting and sold transaction details
  - Added short-term/long-term capital gains breakdown
  - Improved currency formatting across all sheets
  - Added total rows for "Vesting Events" and "Sale Events" sheets

- **FA Reports**:
  - Enhanced currency and number formatting
  - Added totals where applicable
  - Improved column width handling

#### Validation Reporting
- **Comprehensive validation results** with detailed breakdown by data source
- **Transaction-level details** showing exactly what's missing or inconsistent  
- **Overlap analysis** for FY/CY date range validation
- **Clear pass/fail indicators** with specific recommendations

### 🛠️ Technical Improvements

#### Code Architecture
- **New validation module**: `src/equitywise/validation/cross_validator.py`
- **Enhanced settings**: Added Excel temporary file filtering to all discovery methods
- **Improved error handling**: Better exception handling and logging throughout
- **Code organization**: Better separation of concerns for validation logic

#### Configuration Updates
- **Auto-discovery improvements**: Enhanced file discovery with temporary file filtering
- **Validation settings**: Added configuration options for validation behavior
- **Performance optimizations**: Improved data loading and processing efficiency

### 📚 Documentation

#### README Updates
- **Comprehensive validation section**: Detailed documentation of validation features
- **Updated command examples**: Added `--validate` flag examples throughout
- **Enhanced troubleshooting**: Added solutions for common validation and Excel issues
- **Improved feature descriptions**: Better explanation of Excel formatting enhancements

## Usage Examples

### Before (v1.x):
```bash
uv run equitywise calculate-rsu --financial-year FY24-25
```

### After (v2.0):
```bash
# Basic calculation
uv run equitywise calculate-rsu --financial-year FY24-25

# With comprehensive validation (recommended)
uv run equitywise calculate-rsu --financial-year FY24-25 --validate

# Enhanced Excel reports with professional formatting automatically included
```

### Validation Results:
```
✅ Comprehensive validation PASSED!
• BenefitHistory vs RSU PDF: 12 vesting events validated  
• BenefitHistory vs G&L Statement: 8 sale transactions validated
• RSU vs FA overlap: 3 common transactions validated
• Internal consistency: All calculations verified
• 0 warnings
```

## Migration Guide

### For Existing Users
- **No breaking changes**: All existing commands continue to work
- **Recommended**: Add `--validate` flag to ensure data accuracy
- **Automatic**: Enhanced Excel formatting applies to all reports
- **Optional**: Review validation output for any data inconsistencies

### New Users
- **Start with validation**: Use `--validate` flag from the beginning
- **Excel files**: Close Excel files before running EquityWise (temporary files are now automatically handled)
- **Data quality**: Use validation to ensure all data sources are consistent before tax filing

---

*For detailed information about any feature, see the main README.md or run `uv run equitywise help-guide`*
