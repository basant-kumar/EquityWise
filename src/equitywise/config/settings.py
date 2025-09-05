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
    benefit_history_path = "data/user_data/benefit_history/BenefitHistory.xlsx"
    sbi_rates_path = "data/reference_data/exchange_rates/Exchange_Reference_Rates.csv"
    
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
import glob

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings
from loguru import logger


class Settings(BaseSettings):
    """Application settings."""
    
    # ===================================================================================
    # DIRECTORY-BASED AUTO-DISCOVERY (NEW APPROACH)
    # ===================================================================================
    
    # Main data directories - files are automatically discovered
    user_data_dir: Path = Field(
        default=Path("data/user_data"),
        description="Root directory for personal financial data"
    )
    
    reference_data_dir: Path = Field(
        default=Path("data/reference_data"),
        description="Root directory for public market data"
    )
    
    # Subdirectories for different file types
    benefit_history_dir: Path = Field(
        default=Path("data/user_data/benefit_history"),
        description="Directory containing E*Trade BenefitHistory files"
    )
    
    gl_statements_dir: Path = Field(
        default=Path("data/user_data/gl_statements"),
        description="Directory containing E*Trade Gain & Loss statement files"
    )
    
    rsu_documents_dir: Path = Field(
        default=Path("data/user_data/rsu_documents"),
        description="Directory containing RSU vesting statement PDFs from Excelity"
    )
    
    bank_statements_dir: Path = Field(
        default=Path("data/user_data/bank_statements"),
        description="Directory containing bank statement files for reconciliation"
    )
    
    exchange_rates_dir: Path = Field(
        default=Path("data/reference_data/exchange_rates"),
        description="Directory containing SBI TTBR exchange rate files"
    )
    
    adobe_stock_dir: Path = Field(
        default=Path("data/reference_data/adobe_stock"),
        description="Directory containing Adobe stock price history files"
    )
    
    # ===================================================================================
    # LEGACY FILE PATHS (BACKWARD COMPATIBILITY)
    # ===================================================================================
    
    # Data file paths (can be overridden via environment variables or CLI)
    benefit_history_path: Path = Field(
        default=Path("data/user_data/benefit_history/BenefitHistory.xlsx"),
        description="Path to E*Trade BenefitHistory.xlsx file"
    )
    
    # All G&L statement files for comprehensive sales history
    gl_statements_paths: list[Path] = Field(
        default_factory=lambda: [
            Path("data/user_data/gl_statements/G&L_Expanded_2023.xlsx"),
            Path("data/user_data/gl_statements/G&L_Expanded_2024.xlsx"),
            Path("data/user_data/gl_statements/G&L_Expanded_2025.xlsx")
        ],
        description="Paths to all G&L statement files for complete transaction history"
    )
    
    sbi_ttbr_rates_path: Path = Field(
        default=Path("data/reference_data/exchange_rates/Exchange_Reference_Rates.csv"),
        description="Path to SBI TTBR rates CSV file"
    )
    
    adobe_stock_data_path: Path = Field(
        default=Path("data/reference_data/adobe_stock/HistoricalData_1756011612969.csv"),
        description="Path to Adobe stock historical data CSV file"
    )
    
    # Template files for report generation
    fa_declaration_template_path: Path = Field(
        default=Path("data/reference_data/templates/FA_Declaration_Template.csv"),
        description="Path to FA declaration CSV template file for proper column formatting"
    )
    
    # All RSU PDF files for comprehensive vesting history
    rsu_pdf_paths: List[Path] = Field(
        default=[
            Path("data/user_data/rsu_documents/RSU_FY-22-23.pdf"),
            Path("data/user_data/rsu_documents/RSU_FY-23-24.pdf"),
            Path("data/user_data/rsu_documents/RSU_FY-24-25.pdf"),
            Path("data/user_data/rsu_documents/RSU_FY-25-26.pdf")
        ],
        description="Paths to all RSU PDF statement files from Excelity portal for complete vesting history"
    )
    
    # Bank Statement files for transaction reconciliation
    bank_statement_paths: List[Path] = Field(
        default=[
            Path("data/user_data/bank_statements/BankStatement_FY23-24.xls"),
            Path("data/user_data/bank_statements/BankStatement_FY24-25.xls")
        ],
        description="Paths to bank statement files for broker transaction reconciliation"
    )
    
    # Legacy single path for backward compatibility (uses latest RSU)
    rsu_pdf_path: Path = Field(
        default=Path("data/user_data/rsu_documents/RSU_FY-24-25.pdf"),
        description="Path to latest RSU PDF statement file from Excelity portal (for RSU calculations)"
    )
    
    rsu_fy23_24_pdf_path: Path = Field(
        default=Path("data/user_data/rsu_documents/RSU_FY-23-24.pdf"),
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
    
    # Bank statement parsing settings
    bank_remittance_patterns: dict = Field(
        default={
            "default": r'IRM/USD([\d.]+)@([\d.]+)GST([\d.]+)',
            "sbi": r'IRM/USD([\d.]+)@([\d.]+)GST([\d.]+)',
            "hdfc": r'USD\s+([\d.]+)\s+@\s+([\d.]+)\s+GST\s+([\d.]+)',
            "icici": r'USD([\d.]+)/RATE([\d.]+)/GST([\d.]+)',
            "axis": r'FOREX\s+USD([\d.]+)\s+RATE([\d.]+)\s+SERVICE([\d.]+)',
            "kotak": r'REMIT\s+USD([\d.]+)\s+EXRATE([\d.]+)\s+CHARGES([\d.]+)'
        },
        description="""Bank-specific regex patterns for parsing USD remittance details from transaction remarks.
        
        Pattern Format: Each pattern should capture 3 groups: (usd_amount, exchange_rate, charges/gst)
        - Group 1: USD amount (e.g., 6213.87)
        - Group 2: Exchange rate (e.g., 87.0375) 
        - Group 3: Charges/GST amount (e.g., 576)
        
        Examples:
        - SBI: "IRM/USD6213.87@87.0375GST576/INREM/20250204115415"
        - HDFC: "USD 6213.87 @ 87.0375 GST 576 REMITTANCE RECEIVED"
        - ICICI: "USD6213.87/RATE87.0375/GST576"
        - Axis: "FOREX USD6213.87 RATE87.0375 SERVICE576"
        
        To add custom patterns, update this dictionary or use environment variable:
        RSU_FA_BANK_REMITTANCE_PATTERNS='{"mybank": "regex_pattern_here"}'
        """
    )
    
    default_bank_pattern: str = Field(
        default="default",
        description="Default bank pattern key to use for parsing bank statements. Change to match your bank."
    )
    
    # ===================================================================================
    # FILE DISCOVERY METHODS (NEW APPROACH)
    # ===================================================================================
    
    def discover_rsu_pdf_files(self) -> List[Path]:
        """Automatically discover all RSU PDF files in rsu_documents directory.
        
        Returns:
            List of Path objects for all PDF files found, sorted by name
        """
        if not self.rsu_documents_dir.exists():
            logger.warning(f"RSU documents directory not found: {self.rsu_documents_dir}")
            return []
        
        pdf_files = []
        for pattern in ["*.pdf", "*.PDF"]:
            pdf_files.extend(self.rsu_documents_dir.glob(pattern))
        
        # Sort by filename for consistent processing order
        pdf_files.sort(key=lambda x: x.name)
        
        logger.info(f"Discovered {len(pdf_files)} RSU PDF files in {self.rsu_documents_dir}")
        for file in pdf_files:
            logger.debug(f"Found RSU PDF: {file.name}")
        
        return pdf_files
    
    def discover_gl_statement_files(self) -> List[Path]:
        """Automatically discover all G&L statement files in gl_statements directory.
        
        Returns:
            List of Path objects for all Excel files found, sorted by name
        """
        if not self.gl_statements_dir.exists():
            logger.warning(f"G&L statements directory not found: {self.gl_statements_dir}")
            return []
        
        excel_files = []
        for pattern in ["*.xlsx", "*.xls", "*.XLSX", "*.XLS"]:
            excel_files.extend(self.gl_statements_dir.glob(pattern))
        
        # Sort by filename for consistent processing order
        excel_files.sort(key=lambda x: x.name)
        
        logger.info(f"Discovered {len(excel_files)} G&L statement files in {self.gl_statements_dir}")
        for file in excel_files:
            logger.debug(f"Found G&L statement: {file.name}")
        
        return excel_files
    
    def discover_benefit_history_files(self) -> List[Path]:
        """Automatically discover benefit history files in benefit_history directory.
        
        Returns:
            List of Path objects for all Excel files found, sorted by name
        """
        if not self.benefit_history_dir.exists():
            logger.warning(f"Benefit history directory not found: {self.benefit_history_dir}")
            return []
        
        excel_files = []
        for pattern in ["*.xlsx", "*.xls", "*.XLSX", "*.XLS"]:
            excel_files.extend(self.benefit_history_dir.glob(pattern))
        
        # Sort by filename for consistent processing order
        excel_files.sort(key=lambda x: x.name)
        
        logger.info(f"Discovered {len(excel_files)} benefit history files in {self.benefit_history_dir}")
        for file in excel_files:
            logger.debug(f"Found benefit history: {file.name}")
        
        return excel_files
    
    def discover_bank_statement_files(self) -> List[Path]:
        """Automatically discover bank statement files in bank_statements directory.
        
        Returns:
            List of Path objects for all Excel files found, sorted by name
        """
        if not self.bank_statements_dir.exists():
            logger.warning(f"Bank statements directory not found: {self.bank_statements_dir}")
            return []
        
        excel_files = []
        for pattern in ["*.xlsx", "*.xls", "*.XLSX", "*.XLS", "*.xlsm", "*.XLSM"]:
            excel_files.extend(self.bank_statements_dir.glob(pattern))
        
        # Sort by filename for consistent processing order
        excel_files.sort(key=lambda x: x.name)
        
        logger.info(f"Discovered {len(excel_files)} bank statement files in {self.bank_statements_dir}")
        for file in excel_files:
            logger.debug(f"Found bank statement: {file.name}")
        
        return excel_files
    
    def discover_exchange_rate_files(self) -> List[Path]:
        """Automatically discover exchange rate files in exchange_rates directory.
        
        Returns:
            List of Path objects for all CSV files found, sorted by name
        """
        if not self.exchange_rates_dir.exists():
            logger.warning(f"Exchange rates directory not found: {self.exchange_rates_dir}")
            return []
        
        csv_files = []
        for pattern in ["*.csv", "*.CSV"]:
            csv_files.extend(self.exchange_rates_dir.glob(pattern))
        
        # Sort by filename for consistent processing order
        csv_files.sort(key=lambda x: x.name)
        
        logger.info(f"Discovered {len(csv_files)} exchange rate files in {self.exchange_rates_dir}")
        for file in csv_files:
            logger.debug(f"Found exchange rate file: {file.name}")
        
        return csv_files
    
    def discover_adobe_stock_files(self) -> List[Path]:
        """Automatically discover Adobe stock data files in adobe_stock directory.
        
        Returns:
            List of Path objects for all CSV files found, sorted by name
        """
        if not self.adobe_stock_dir.exists():
            logger.warning(f"Adobe stock directory not found: {self.adobe_stock_dir}")
            return []
        
        csv_files = []
        for pattern in ["*.csv", "*.CSV"]:
            csv_files.extend(self.adobe_stock_dir.glob(pattern))
        
        # Sort by filename for consistent processing order
        csv_files.sort(key=lambda x: x.name)
        
        logger.info(f"Discovered {len(csv_files)} Adobe stock files in {self.adobe_stock_dir}")
        for file in csv_files:
            logger.debug(f"Found Adobe stock file: {file.name}")
        
        return csv_files
    
    def get_rsu_files(self, use_auto_discovery: bool = True) -> List[Path]:
        """Get RSU files using either auto-discovery or configured paths.
        
        Args:
            use_auto_discovery: If True, use auto-discovery; if False, use configured paths
            
        Returns:
            List of RSU PDF file paths
        """
        if use_auto_discovery:
            discovered = self.discover_rsu_pdf_files()
            if discovered:
                return discovered
            else:
                logger.warning("No RSU files found via auto-discovery, falling back to configured paths")
        
        # Fallback to configured paths
        existing_paths = [path for path in self.rsu_pdf_paths if path.exists()]
        if not existing_paths:
            logger.warning("No RSU files found in configured paths either")
        return existing_paths
    
    def get_gl_statement_files(self, use_auto_discovery: bool = True) -> List[Path]:
        """Get G&L statement files using either auto-discovery or configured paths.
        
        Args:
            use_auto_discovery: If True, use auto-discovery; if False, use configured paths
            
        Returns:
            List of G&L statement file paths
        """
        if use_auto_discovery:
            discovered = self.discover_gl_statement_files()
            if discovered:
                return discovered
            else:
                logger.warning("No G&L files found via auto-discovery, falling back to configured paths")
        
        # Fallback to configured paths
        existing_paths = [path for path in self.gl_statements_paths if path.exists()]
        if not existing_paths:
            logger.warning("No G&L files found in configured paths either")
        return existing_paths
    
    # ===================================================================================
    # BANK PATTERN MANAGEMENT METHODS
    # ===================================================================================
    
    def get_available_bank_patterns(self) -> dict:
        """Get all available bank patterns.
        
        Returns:
            Dictionary of bank_name -> regex_pattern
        """
        return self.bank_remittance_patterns.copy()
    
    def add_bank_pattern(self, bank_name: str, pattern: str, set_as_default: bool = False) -> bool:
        """Add a custom bank pattern.
        
        Args:
            bank_name: Name/key for the bank pattern
            pattern: Regex pattern that captures (usd_amount, exchange_rate, charges)
            set_as_default: If True, set this pattern as the default
            
        Returns:
            True if pattern was added successfully, False if validation failed
        """
        # Validate pattern has exactly 3 capture groups
        import re
        try:
            compiled = re.compile(pattern)
            if compiled.groups != 3:
                logger.error(f"Bank pattern must have exactly 3 capture groups, got {compiled.groups}")
                return False
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return False
        
        # Add pattern
        self.bank_remittance_patterns[bank_name] = pattern
        logger.info(f"Added bank pattern '{bank_name}': {pattern}")
        
        # Set as default if requested
        if set_as_default:
            self.default_bank_pattern = bank_name
            logger.info(f"Set '{bank_name}' as default bank pattern")
            
        return True
    
    def test_bank_pattern(self, pattern: str, test_string: str) -> Optional[dict]:
        """Test a bank pattern against a sample transaction string.
        
        Args:
            pattern: Regex pattern to test
            test_string: Sample transaction remark string
            
        Returns:
            Dictionary with extracted values if successful, None if no match
        """
        import re
        try:
            match = re.search(pattern, test_string)
            if match:
                return {
                    'usd_amount': float(match.group(1)),
                    'exchange_rate': float(match.group(2)), 
                    'charges_gst': float(match.group(3)),
                    'pattern_matched': True
                }
        except (ValueError, AttributeError, re.error) as e:
            logger.error(f"Pattern test failed: {e}")
            
        return None
    
    def validate_bank_patterns(self) -> bool:
        """Validate all configured bank patterns.
        
        Returns:
            True if all patterns are valid, False otherwise
        """
        import re
        all_valid = True
        
        for bank_name, pattern in self.bank_remittance_patterns.items():
            try:
                compiled = re.compile(pattern)
                if compiled.groups != 3:
                    logger.error(f"Bank pattern '{bank_name}' has {compiled.groups} groups, expected 3")
                    all_valid = False
                else:
                    logger.debug(f"Bank pattern '{bank_name}' is valid")
            except re.error as e:
                logger.error(f"Bank pattern '{bank_name}' is invalid: {e}")
                all_valid = False
                
        return all_valid
    
    model_config = ConfigDict(
        env_file=".env",
        env_prefix="RSU_FA_",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
