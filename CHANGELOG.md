# Changelog

All notable changes to EquityWise will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-08-30

### 🎯 Major Rebrand - EquityWise

#### Changed
- **Project Name**: Renamed from "RSU FA Tool" to "EquityWise" 
- **CLI Command**: Changed from `rsu-fa-tool` to `equitywise`
- **Description**: Enhanced to emphasize E*Trade data processing and broader equity support (RSU, ESPP)
- **Tagline**: "Smart equity tax calculations from E*Trade data"

#### Added
- Total row for Sale Proceeds in Foreign Assets vest-wise details table (console and Excel)
- Enhanced .gitignore for better project organization
- Generic placeholder data for easier open-source distribution

#### Technical
- Updated all documentation (README.md, USER_GUIDE.md, CHANGELOG.md)
- Updated package metadata in pyproject.toml
- Prepared for GitHub publication under new name

## [1.0.0] - 2025-08-26

### 🎉 Initial Release - Production Ready

This is the first production-ready release of the RSU FA Tool, providing comprehensive RSU tax calculations and Foreign Assets compliance for Indian tax law.

### ✨ Features

#### Core Calculation Engines
- **RSU Tax Calculator**: Complete capital gains/loss calculations for Indian Financial Years
- **Foreign Assets Calculator**: FA declaration requirements for Calendar Years
- **Multi-format Reports**: Professional Excel and CSV reports with bank reconciliation
- **Interactive CLI**: Guided workflows with progress tracking and error recovery

#### Data Processing
- **E*Trade Integration**: Parse BenefitHistory.xlsx and Gain/Loss statements
- **SBI TTBR Rates**: Automatic USD-INR exchange rate lookup with fallback logic
- **Adobe Stock Data**: Historical stock price integration with trading day fallback
- **Bank Reconciliation**: Track RSU proceeds and transfer expenses

#### Advanced Features
- **FIFO Cost Basis**: Accurate cost basis calculations using First-In-First-Out method
- **Holding Period Classification**: Automatic short-term vs long-term capital gains (24-month rule)
- **Multi-year Support**: Process multiple financial/calendar years simultaneously
- **Data Validation**: Comprehensive validation with detailed error reporting

### 🛠️ Technical Implementation

#### Architecture
- **Modular Design**: Clean separation of calculators, data loaders, and reports
- **Type Safety**: Full Pydantic validation and type hints throughout
- **Error Handling**: Robust error recovery with detailed user guidance
- **Performance**: Optimized for large datasets (tested with 4,279 records in 2.2 seconds)

#### Testing & Quality
- **Comprehensive Test Suite**: 9/9 test suites passing (121 total tests)
- **Integration Testing**: End-to-end validation with real production data
- **Code Coverage**: High coverage across all critical calculation paths
- **Data Validation**: Extensive validation of all input file formats

### 📊 Validation Results

#### Production Data Testing
- **RSU Calculations**: ₹15,07,011.83 in vesting events and ₹9,57,543.21 in sales validated
- **FA Compliance**: ₹4,23,455.76 year-end holdings with ₹4,33,160.00 peak balance
- **Multi-year Processing**: 4 years of data (2022-2025) processed successfully
- **Bank Reconciliation**: Transfer expenses and proceeds tracking validated

#### Performance Benchmarks
- **Test Execution**: 8.58 seconds for complete test suite
- **Complex Calculations**: 2.2 seconds for 4-year, 4,279-record processing
- **Memory Efficiency**: Optimized for large datasets with minimal memory footprint
- **Error Recovery**: Graceful handling of missing data with intelligent fallbacks

### 🎯 Tax Compliance

#### Indian Tax Law Support
- **Financial Year Calculations**: April-March tax year support
- **Capital Gains Classification**: Short-term (<24 months) vs Long-term (>24 months)
- **Foreign Assets Compliance**: ₹2 lakh threshold with peak balance tracking
- **ITR-2 Integration**: Ready-to-use data for Schedule Capital Gains and Schedule FA

#### Accuracy Validation
- **Cross-validation**: Manual calculation verification for all formulas
- **E*Trade Consistency**: Calculations match broker-provided adjusted cost basis
- **SBI Rate Accuracy**: Exchange rates verified against SBI TTBR official data
- **Adobe Stock Verification**: Stock prices cross-checked with Yahoo Finance data

### 📚 Documentation

#### User Documentation
- **README.md**: Comprehensive setup and usage guide
- **USER_GUIDE.md**: 50+ section step-by-step tutorial with examples
- **Help System**: Built-in CLI help with detailed command documentation
- **Troubleshooting**: Common issues and solutions guide

#### Developer Documentation
- **Code Documentation**: Enhanced inline documentation for all modules
- **API Reference**: Complete type hints and docstrings
- **Testing Guide**: Test suite documentation and development setup
- **Configuration**: Environment variables and settings customization

### 🔧 Installation & Setup

#### Requirements
- Python 3.11+ (tested on 3.11.13)
- UV package manager (recommended) or pip
- Excel/LibreOffice for viewing reports

#### Data Files Required
- E*Trade BenefitHistory.xlsx
- E*Trade Gain/Loss statements
- Adobe stock price history
- SBI TTBR exchange rates
- Bank statements (optional)

### 🚀 Getting Started

```bash
# Install using UV (recommended)
uv sync

# Interactive mode for first-time users
uv run rsu-fa-tool

# Calculate RSU taxes for FY24-25
uv run rsu-fa-tool calculate-rsu --financial-year FY24-25 --output-format excel

# Check FA declaration requirement
uv run rsu-fa-tool calculate-fa --calendar-year 2024 --check-only
```

### 🙏 Acknowledgments

- **Adobe Inc.** for comprehensive RSU program documentation
- **E*Trade** for detailed transaction data export capabilities
- **SBI** for TTBR exchange rate data availability
- **Indian Income Tax Department** for clear FA declaration guidelines

### ⚠️ Important Notes

- This tool provides calculations for reference purposes only
- Always consult with a qualified tax professional for complex scenarios
- Verify all calculations before filing tax returns
- Keep original source files for audit purposes

---

## Future Releases

Stay tuned for upcoming features:
- Automated SBI rate fetching
- Multi-broker support (beyond E*Trade)
- Direct ITR-2 XML export
- Advanced reporting templates
- Tax optimization recommendations

For feature requests or bug reports, please open an issue on GitHub.

