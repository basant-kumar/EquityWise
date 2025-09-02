"""
Configuration settings for RSU FA Tool.

This module defines the application configuration using Pydantic Settings
for type-safe, environment-aware configuration management. Settings can be
overridden via environment variables, CLI arguments, or configuration files.

Key Configuration Categories:

1. **Data File Paths**:
   - benefit_history_path: E*Trade BenefitHistory.xlsx location
   - gl_statements_paths: List of Gain/Loss statement files
   - sbi_rates_path: SBI TTBR exchange rates file
   - adobe_stock_path: Adobe stock price history file
   - bank_statement_path: Bank statement for reconciliation

2. **Calculation Parameters**:
   - fa_declaration_threshold_inr: FA declaration threshold (₹2,00,000)
   - fallback_days_exchange_rate: Days to search for missing rates (7)
   - fallback_days_stock_price: Days to search for missing prices (15)

3. **Output Settings**:
   - output_dir: Directory for generated reports
   - log_level: Logging verbosity (INFO, DEBUG, ERROR)
   - excel_formatting: Enable Excel formatting and styling

Environment Variable Overrides:
- RSU_BENEFIT_HISTORY_PATH: Override benefit history file path
- RSU_GL_STATEMENTS_PATHS: Override G&L statement paths (comma-separated)
- RSU_OUTPUT_DIR: Override output directory
- RSU_LOG_LEVEL: Override logging level

Configuration File Support:
Place settings.toml in config/ directory:
    [data_paths]
    benefit_history_path = "data/user_data/BenefitHistory.xlsx"
    sbi_rates_path = "data/reference_data/Exchange_Reference_Rates.csv"
    
    [calculation_settings]
    fa_declaration_threshold_inr = 200000.0
    fallback_days_exchange_rate = 7

Example Usage:
    from equitywise.config.settings import settings
    
    # Access configuration
    benefit_path = settings.benefit_history_path
    threshold = settings.fa_declaration_threshold_inr
    
    # Override via environment
    import os
    os.environ["RSU_LOG_LEVEL"] = "DEBUG"
"""

from pathlib import Path
from typing import Optional, List

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Data file paths (can be overridden via environment variables or CLI)
    benefit_history_path: Path = Field(
        default=Path("data/user_data/BenefitHistory.xlsx"),
        description="Path to E*Trade BenefitHistory.xlsx file"
    )
    
    # All G&L statement files for comprehensive sales history
    gl_statements_paths: list[Path] = Field(
        default_factory=lambda: [
            Path("data/user_data/G&L_Expanded_2023.xlsx"),
            Path("data/user_data/G&L_Expanded_2024.xlsx"),
            Path("data/user_data/G&L_Expanded_2025.xlsx")
        ],
        description="Paths to all G&L statement files for complete transaction history"
    )
    
    sbi_ttbr_rates_path: Path = Field(
        default=Path("data/reference_data/Exchange_Reference_Rates.csv"),
        description="Path to SBI TTBR rates CSV file"
    )
    
    adobe_stock_data_path: Path = Field(
        default=Path("data/reference_data/HistoricalData_1756011612969.csv"),
        description="Path to Adobe stock historical data CSV file"
    )
    
    # All RSU PDF files for comprehensive vesting history
    rsu_pdf_paths: List[Path] = Field(
        default=[
            Path("data/user_data/RSU_FY-22-23.pdf"),
            Path("data/user_data/RSU_FY-23-24.pdf"),
            Path("data/user_data/RSU_FY-24-25.pdf"),
             Path("data/user_data/RSU_FY-25-26.pdf")
        ],
        description="Paths to all RSU PDF statement files from Excelity portal for complete vesting history"
    )
    
    # Bank Statement files for transaction reconciliation
    bank_statement_paths: List[Path] = Field(
        default=[
            Path("data/user_data/BankStatement_FY23-24.xls"),
            Path("data/user_data/BankStatement_FY24-25.xls")
        ],
        description="Paths to bank statement files for broker transaction reconciliation"
    )
    
    # Legacy single path for backward compatibility (uses latest RSU)
    rsu_pdf_path: Path = Field(
        default=Path("data/user_data/RSU_FY-24-25.pdf"),
        description="Path to latest RSU PDF statement file from Excelity portal (for RSU calculations)"
    )
    
    rsu_fy23_24_pdf_path: Path = Field(
        default=Path("data/user_data/RSU_FY-23-24.pdf"),
        description="Path to RSU PDF statement file (FY23-24) from Excelity portal - legacy compatibility"
    )
    
    # Output settings
    output_dir: Path = Field(
        default=Path("output"),
        description="Directory for generated reports"
    )
    
    # Financial year settings
    financial_year: Optional[str] = Field(
        default=None,
        description="Financial year for RSU calculations (e.g., 'FY2024')"
    )
    
    calendar_year: Optional[int] = Field(
        default=None,
        description="Calendar year for Foreign Assets calculations"
    )
    
    # Logging settings
    log_level: str = Field(default="INFO", description="Log level")
    log_file: Optional[Path] = Field(default=None, description="Log file path")
    
    # Currency settings
    base_currency: str = Field(default="INR", description="Base currency for calculations")
    
    model_config = ConfigDict(
        env_file=".env",
        env_prefix="RSU_FA_",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
