"""Data loading utilities for RSU FA Tool."""

from pathlib import Path
from typing import Optional, List, Dict, Any
import warnings

import pandas as pd
from loguru import logger
from pydantic import ValidationError

from .models import (
    BenefitHistoryRecord, 
    GLStatementRecord, 
    SBIRateRecord, 
    AdobeStockRecord,
    ESOPVestingRecord,
    BankStatementRecord
)
from .esop_parser import ESOPParser


class DataLoader:
    """Base class for data loading utilities."""
    
    def __init__(self, file_path: Path):
        """Initialize the data loader.
        
        Args:
            file_path: Path to the data file.
        """
        self.file_path = file_path
        self._data: Optional[pd.DataFrame] = None
    
    def load_data(self) -> pd.DataFrame:
        """Load data from file.
        
        Returns:
            DataFrame with loaded data.
            
        Raises:
            FileNotFoundError: If file doesn't exist.
            Exception: If data loading fails.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.file_path}")
        
        try:
            logger.info(f"Loading data from {self.file_path}")
            self._data = self._load_file()
            logger.info(f"Loaded {len(self._data)} records")
            return self._data
        except Exception as e:
            logger.error(f"Failed to load data from {self.file_path}: {e}")
            raise
    
    def _load_file(self) -> pd.DataFrame:
        """Load the specific file format. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _load_file method")
    
    @property
    def data(self) -> Optional[pd.DataFrame]:
        """Get loaded data."""
        return self._data


class BenefitHistoryLoader(DataLoader):
    """Loader for E*Trade BenefitHistory.xlsx file."""
    
    def _load_file(self) -> pd.DataFrame:
        """Load BenefitHistory Excel file."""
        try:
            # Suppress pandas warnings for cleaner output
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                df = pd.read_excel(self.file_path)
            
            logger.info(f"BenefitHistory file has {len(df)} rows and {len(df.columns)} columns")
            logger.debug(f"Columns: {list(df.columns)}")
            
            # Clean the data
            df = self._clean_benefit_history(df)
            
            return df
        except Exception as e:
            logger.error(f"Failed to parse BenefitHistory.xlsx: {e}")
            raise
    
    def _clean_benefit_history(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess BenefitHistory data."""
        # Remove rows where all important columns are NaN
        important_cols = ['Record Type', 'Symbol', 'Grant Date', 'Vest Date']
        
        # Keep rows that have at least one non-null value in important columns
        mask = df[important_cols].notna().any(axis=1)
        df_cleaned = df[mask].copy()
        
        # Convert date columns with explicit format to avoid warnings
        date_columns = ['Grant Date', 'Vest Date', 'Date']
        for col in date_columns:
            if col in df_cleaned.columns:
                df_cleaned[col] = pd.to_datetime(df_cleaned[col], format='%m/%d/%Y', errors='coerce')
        
        logger.info(f"Cleaned BenefitHistory: {len(df_cleaned)} valid rows from {len(df)} total")
        
        return df_cleaned
    
    def get_validated_records(self) -> List[BenefitHistoryRecord]:
        """Get validated BenefitHistoryRecord objects."""
        if self._data is None:
            self.load_data()
        
        records = []
        validation_errors = []
        
        for idx, row in self._data.iterrows():
            try:
                # Clean up NaN values before validation
                row_dict = row.to_dict()
                cleaned_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
                
                record = BenefitHistoryRecord(**cleaned_dict)
                records.append(record)
            except ValidationError as e:
                validation_errors.append(f"Row {idx}: {e}")
                logger.debug(f"Validation error for row {idx}: {e}")
            except Exception as e:
                validation_errors.append(f"Row {idx}: Unexpected error - {e}")
                logger.debug(f"Unexpected error for row {idx}: {e}")
        
        logger.info(f"Validated {len(records)} BenefitHistory records, {len(validation_errors)} errors")
        
        if validation_errors and len(validation_errors) > 10:
            logger.warning(f"Found {len(validation_errors)} validation errors in BenefitHistory (showing first 5)")
            for error in validation_errors[:5]:
                logger.debug(error)
        
        return records
    
    def get_records_as_dicts(self) -> List[dict]:
        """Get BenefitHistory records as dictionaries (backup method)."""
        if self._data is None:
            self.load_data()
        
        records = []
        for idx, row in self._data.iterrows():
            record = row.to_dict()
            cleaned_record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
            records.append(cleaned_record)
        
        logger.info(f"Converted {len(records)} BenefitHistory records to dictionaries")
        return records


class GLStatementLoader(DataLoader):
    """Loader for G&L statement Excel files."""
    
    def _load_file(self) -> pd.DataFrame:
        """Load G&L statement Excel file."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                df = pd.read_excel(self.file_path)
            
            logger.info(f"G&L statement file has {len(df)} rows and {len(df.columns)} columns")
            logger.debug(f"File: {self.file_path.name}")
            
            # Clean the data
            df = self._clean_gl_statement(df)
            
            return df
        except Exception as e:
            logger.error(f"Failed to parse G&L statement {self.file_path.name}: {e}")
            raise
    
    def _clean_gl_statement(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess G&L statement data."""
        # Filter out summary rows and keep only actual transactions
        df_cleaned = df[df['Record Type'] != 'Summary'].copy()
        
        # Convert date columns with explicit format to avoid warnings
        date_columns = ['Date Acquired', 'Date Sold', 'Grant Date', 'Vest Date']
        for col in date_columns:
            if col in df_cleaned.columns:
                df_cleaned[col] = pd.to_datetime(df_cleaned[col], format='%m/%d/%Y', errors='coerce')
        
        # Convert numeric columns
        numeric_columns = [
            'Quantity', 'Acquisition Cost', 'Total Proceeds', 'Gain/Loss',
            'Grant Date FMV', 'Vest Date FMV', 'Order Number'
        ]
        for col in numeric_columns:
            if col in df_cleaned.columns:
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        
        logger.info(f"Cleaned G&L statement: {len(df_cleaned)} transaction rows from {len(df)} total")
        
        return df_cleaned
    
    def get_validated_records(self) -> List[GLStatementRecord]:
        """Get validated GLStatementRecord objects."""
        if self._data is None:
            self.load_data()
        
        records = []
        validation_errors = []
        
        for idx, row in self._data.iterrows():
            try:
                row_dict = row.to_dict()
                cleaned_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
                
                record = GLStatementRecord(**cleaned_dict)
                records.append(record)
            except ValidationError as e:
                validation_errors.append(f"Row {idx}: {e}")
                logger.debug(f"Validation error for row {idx}: {e}")
            except Exception as e:
                validation_errors.append(f"Row {idx}: Unexpected error - {e}")
                logger.debug(f"Unexpected error for row {idx}: {e}")
        
        logger.info(f"Validated {len(records)} G&L statement records, {len(validation_errors)} errors")
        return records
    
    def get_records_as_dicts(self) -> List[dict]:
        """Get G&L statement records as dictionaries (backup method)."""
        if self._data is None:
            self.load_data()
        
        records = []
        for idx, row in self._data.iterrows():
            record = row.to_dict()
            cleaned_record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
            records.append(cleaned_record)
        
        logger.info(f"Converted {len(records)} G&L statement records to dictionaries")
        return records


class SBIRatesLoader(DataLoader):
    """Loader for SBI TTBR rates CSV file."""
    
    def _load_file(self) -> pd.DataFrame:
        """Load SBI rates CSV file."""
        try:
            # Skip the first 2 header lines (Financial Benchmarks India Pvt Ltd, Reference Rates)
            df = pd.read_csv(self.file_path, skiprows=2)
            
            logger.info(f"SBI rates file has {len(df)} rows and {len(df.columns)} columns")
            logger.debug(f"Columns: {list(df.columns)}")
            
            # Clean the data
            df = self._clean_sbi_rates(df)
            
            return df
        except Exception as e:
            logger.error(f"Failed to parse SBI rates CSV: {e}")
            raise
    
    def _clean_sbi_rates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess SBI rates data."""
        # Remove any empty rows
        df_cleaned = df.dropna(how='all').copy()
        
        # Convert Date column
        df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], format='%d %b %Y', errors='coerce')
        
        # Convert Rate column to numeric
        df_cleaned['Rate'] = pd.to_numeric(df_cleaned['Rate'], errors='coerce')
        
        # Filter for USD rates only (most relevant for RSU calculations)
        usd_rates = df_cleaned[df_cleaned['Currency Pairs'].str.contains('USD', na=False)].copy()
        
        logger.info(f"Cleaned SBI rates: {len(usd_rates)} USD rate records from {len(df)} total")
        
        return usd_rates
    
    def get_validated_records(self) -> List[SBIRateRecord]:
        """Get validated SBIRateRecord objects."""
        if self._data is None:
            self.load_data()
        
        records = []
        validation_errors = []
        
        for idx, row in self._data.iterrows():
            try:
                row_dict = row.to_dict()
                cleaned_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
                
                record = SBIRateRecord(**cleaned_dict)
                records.append(record)
            except ValidationError as e:
                validation_errors.append(f"Row {idx}: {e}")
                logger.debug(f"Validation error for row {idx}: {e}")
            except Exception as e:
                validation_errors.append(f"Row {idx}: Unexpected error - {e}")
                logger.debug(f"Unexpected error for row {idx}: {e}")
        
        logger.info(f"Validated {len(records)} SBI rate records, {len(validation_errors)} errors")
        return records
    
    def get_records_as_dicts(self) -> List[dict]:
        """Get SBI rate records as dictionaries (backup method)."""
        if self._data is None:
            self.load_data()
        
        records = []
        for idx, row in self._data.iterrows():
            record = row.to_dict()
            cleaned_record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
            records.append(cleaned_record)
        
        logger.info(f"Converted {len(records)} SBI rate records to dictionaries")
        return records


class AdobeStockDataLoader(DataLoader):
    """Loader for Adobe stock historical data CSV file."""
    
    def _load_file(self) -> pd.DataFrame:
        """Load Adobe stock data CSV file."""
        try:
            df = pd.read_csv(self.file_path)
            
            logger.info(f"Adobe stock data file has {len(df)} rows and {len(df.columns)} columns")
            logger.debug(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
            
            # Clean the data
            df = self._clean_stock_data(df)
            
            return df
        except Exception as e:
            logger.error(f"Failed to parse Adobe stock data CSV: {e}")
            raise
    
    def _clean_stock_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess Adobe stock data."""
        df_cleaned = df.copy()
        
        # Convert Date column with explicit format to avoid warnings
        df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], format='%m/%d/%Y', errors='coerce')
        
        # Convert price columns (remove $ sign and convert to float)
        price_columns = ['Close/Last', 'Open', 'High', 'Low']
        for col in price_columns:
            if col in df_cleaned.columns:
                df_cleaned[col] = df_cleaned[col].astype(str).str.replace('$', '').str.replace(',', '')
                df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        
        # Convert Volume to numeric
        df_cleaned['Volume'] = pd.to_numeric(df_cleaned['Volume'], errors='coerce')
        
        # Sort by date (most recent first)
        df_cleaned = df_cleaned.sort_values('Date', ascending=False)
        
        # Remove any rows with invalid data
        df_cleaned = df_cleaned.dropna(subset=['Date', 'Close/Last'])
        
        logger.info(f"Cleaned Adobe stock data: {len(df_cleaned)} valid records")
        
        return df_cleaned
    
    def get_validated_records(self) -> List[AdobeStockRecord]:
        """Get validated AdobeStockRecord objects."""
        if self._data is None:
            self.load_data()
        
        records = []
        validation_errors = []
        
        for idx, row in self._data.iterrows():
            try:
                row_dict = row.to_dict()
                cleaned_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
                
                record = AdobeStockRecord(**cleaned_dict)
                records.append(record)
            except ValidationError as e:
                validation_errors.append(f"Row {idx}: {e}")
                logger.debug(f"Validation error for row {idx}: {e}")
            except Exception as e:
                validation_errors.append(f"Row {idx}: Unexpected error - {e}")
                logger.debug(f"Unexpected error for row {idx}: {e}")
        
        logger.info(f"Validated {len(records)} Adobe stock records, {len(validation_errors)} errors")
        return records
    
    def get_records_as_dicts(self) -> List[dict]:
        """Get Adobe stock records as dictionaries (backup method)."""
        if self._data is None:
            self.load_data()
        
        records = []
        for idx, row in self._data.iterrows():
            record = row.to_dict()
            cleaned_record = {k: (None if pd.isna(v) else v) for k, v in record.items()}
            records.append(cleaned_record)
        
        logger.info(f"Converted {len(records)} Adobe stock records to dictionaries")
        return records


class MultiFileLoader:
    """Utility to load multiple related files."""
    
    def __init__(self):
        """Initialize the multi-file loader."""
        self.loaders: Dict[str, DataLoader] = {}
    
    def add_loader(self, name: str, loader: DataLoader) -> None:
        """Add a data loader.
        
        Args:
            name: Name identifier for the loader.
            loader: DataLoader instance.
        """
        self.loaders[name] = loader
    
    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load data from all registered loaders.
        
        Returns:
            Dictionary mapping loader names to DataFrames.
        """
        results = {}
        for name, loader in self.loaders.items():
            try:
                results[name] = loader.load_data()
            except Exception as e:
                logger.error(f"Failed to load {name}: {e}")
                results[name] = None
        
        return results
    
    def get_all_validated_records(self) -> Dict[str, Any]:
        """Get validated records from all loaders.
        
        Returns:
            Dictionary mapping loader names to validated records.
        """
        results = {}
        for name, loader in self.loaders.items():
            try:
                if hasattr(loader, 'get_validated_records'):
                    results[name] = loader.get_validated_records()
                else:
                    logger.warning(f"Loader {name} does not support validation")
                    results[name] = None
            except Exception as e:
                logger.error(f"Failed to get validated records from {name}: {e}")
                results[name] = None
        
        return results
    
    def get_all_records_as_dicts(self) -> Dict[str, Any]:
        """Get records from all loaders as dictionaries (backup method).
        
        Returns:
            Dictionary mapping loader names to record dictionaries.
        """
        results = {}
        for name, loader in self.loaders.items():
            try:
                if hasattr(loader, 'get_records_as_dicts'):
                    results[name] = loader.get_records_as_dicts()
                else:
                    logger.warning(f"Loader {name} does not support dict conversion")
                    results[name] = None
            except Exception as e:
                logger.error(f"Failed to get dict records from {name}: {e}")
                results[name] = None
        
        return results


class DataValidator:
    """Comprehensive data validation utility."""
    
    def __init__(self):
        """Initialize the data validator."""
        self.validation_results = {}
    
    def validate_all_sources(
        self, 
        benefit_history_path: Path,
        gl_paths: List[Path],
        sbi_rates_path: Path,
        stock_data_path: Path
    ) -> Dict[str, Any]:
        """Validate all data sources and return comprehensive results.
        
        Args:
            benefit_history_path: Path to BenefitHistory.xlsx
            gl_paths: List of paths to G&L statement files
            sbi_rates_path: Path to SBI rates CSV
            stock_data_path: Path to Adobe stock data CSV
            
        Returns:
            Dictionary with validation results and loaded data.
        """
        validation_results = {
            'success': True,
            'errors': [],
            'data': {},
            'summary': {}
        }
        
        # Validate BenefitHistory
        try:
            benefit_loader = BenefitHistoryLoader(benefit_history_path)
            benefit_records = benefit_loader.get_validated_records()
            validation_results['data']['benefit_history'] = benefit_records
            validation_results['summary']['benefit_history'] = len(benefit_records)
            logger.info(f"✓ BenefitHistory validation successful: {len(benefit_records)} records")
        except Exception as e:
            validation_results['success'] = False
            validation_results['errors'].append(f"BenefitHistory: {e}")
            logger.error(f"✗ BenefitHistory validation failed: {e}")
        
        # Validate G&L statements
        gl_data = {}
        for gl_path in gl_paths:
            try:
                gl_loader = GLStatementLoader(gl_path)
                gl_records = gl_loader.get_validated_records()
                year = gl_path.name.split('_')[-1].replace('.xlsx', '')
                gl_data[f'gl_{year}'] = gl_records
                logger.info(f"✓ G&L {year} validation successful: {len(gl_records)} records")
            except Exception as e:
                validation_results['success'] = False
                validation_results['errors'].append(f"G&L {gl_path.name}: {e}")
                logger.error(f"✗ G&L {gl_path.name} validation failed: {e}")
        
        validation_results['data']['gl_statements'] = gl_data
        validation_results['summary']['gl_statements'] = sum(len(records) for records in gl_data.values())
        
        # Validate SBI rates
        try:
            sbi_loader = SBIRatesLoader(sbi_rates_path)
            sbi_records = sbi_loader.get_validated_records()
            validation_results['data']['sbi_rates'] = sbi_records
            validation_results['summary']['sbi_rates'] = len(sbi_records)
            logger.info(f"✓ SBI rates validation successful: {len(sbi_records)} records")
        except Exception as e:
            validation_results['success'] = False
            validation_results['errors'].append(f"SBI Rates: {e}")
            logger.error(f"✗ SBI rates validation failed: {e}")
        
        # Validate Adobe stock data
        try:
            stock_loader = AdobeStockDataLoader(stock_data_path)
            stock_records = stock_loader.get_validated_records()
            validation_results['data']['stock_data'] = stock_records
            validation_results['summary']['stock_data'] = len(stock_records)
            logger.info(f"✓ Adobe stock data validation successful: {len(stock_records)} records")
        except Exception as e:
            validation_results['success'] = False
            validation_results['errors'].append(f"Adobe Stock Data: {e}")
            logger.error(f"✗ Adobe stock data validation failed: {e}")
        
        return validation_results


class ESOPLoader(DataLoader):
    """Loader for ESOP PDF vesting data."""
    
    def _load_file(self, file_path: Path) -> pd.DataFrame:
        """Load ESOP PDF file and extract vesting data."""
        parser = ESOPParser(str(file_path))
        df = parser.to_dataframe()
        logger.info(f"ESOP PDF file has {len(df)} vesting records")
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean ESOP vesting data."""
        # Data is already cleaned by the ESOP parser
        logger.info(f"ESOP vesting data: {len(df)} records")
        return df
    
    def get_validated_records(self, file_path: str) -> List[ESOPVestingRecord]:
        """Load and validate ESOP vesting records."""
        parser = ESOPParser(file_path)
        records = parser.extract_vesting_data()
        
        validation_errors = []
        validated_records = []
        
        for i, record in enumerate(records):
            try:
                validated_records.append(record)  # Already validated by ESOPParser
            except ValidationError as e:
                validation_errors.append(f"Row {i}: {e}")
        
        if validation_errors:
            logger.warning(f"ESOP validation errors: {len(validation_errors)}")
            for error in validation_errors[:5]:  # Show first 5 errors
                logger.warning(f"  {error}")
                
        logger.info(f"Validated {len(validated_records)} ESOP vesting records, {len(validation_errors)} errors")
        return validated_records


class BankStatementLoader(DataLoader):
    """Loader for bank statement files."""
    
    def _load_file(self) -> pd.DataFrame:
        """Load bank statement Excel file with proper header detection."""
        try:
            # Read the raw file first
            df_raw = pd.read_excel(self.file_path)
            
            # Find the header row by looking for the transaction data headers
            header_row = None
            for i, row in df_raw.iterrows():
                row_values = [str(val).lower() for val in row.dropna().tolist()]
                if 's no.' in ' '.join(row_values) and 'value date' in ' '.join(row_values):
                    header_row = i
                    logger.info(f"Found bank statement header at row {i}")
                    break
            
            if header_row is None:
                raise ValueError("Could not find bank statement header row")
            
            # Re-read with proper header
            df = pd.read_excel(self.file_path, header=header_row)
            
            # Clean up the dataframe
            df = self._clean_bank_statement(df)
            
            logger.info(f"Bank statement file has {len(df)} rows and {len(df.columns)} columns")
            return df
            
        except Exception as e:
            logger.error(f"Error loading bank statement file {self.file_path}: {e}")
            raise
    
    def _clean_bank_statement(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and process bank statement data."""
        # Remove rows that are just headers or empty
        # Use column 1 (serial number column) since column 0 is always NaN
        df_clean = df.dropna(subset=[df.columns[1]])  # Remove rows with empty serial number column
        
        # Remove rows where the second column (index 1) is not numeric (serial number)
        # Based on debug output, serial numbers are in column 1, not column 0
        def is_numeric_row(x):
            try:
                if pd.isna(x):
                    return False
                int(str(x).replace('.0', ''))  # Handle float serial numbers
                return True
            except (ValueError, TypeError):
                return False
        
        # Filter by column 1 (serial number column) and remove header row
        df_clean = df_clean[df_clean.iloc[:, 1].apply(is_numeric_row)]
        
        # Reset index
        df_clean = df_clean.reset_index(drop=True)
        
        logger.info(f"Cleaned bank statement: {len(df_clean)} transaction rows from {len(df)} total")
        return df_clean
    
    def get_validated_records(self, file_path: str) -> List[BankStatementRecord]:
        """Load and validate bank statement records."""
        loader = BankStatementLoader(Path(file_path))
        df = loader.load_data()
        
        validation_errors = []
        validated_records = []
        
        for i, row in df.iterrows():
            try:
                # Map the DataFrame columns to the model fields (corrected column indices)
                record_data = {
                    "S No.": row.iloc[1],  # Serial number is in column 1
                    "Value Date": row.iloc[2],
                    "Transaction Date": row.iloc[3],
                    "Cheque Number": row.iloc[4],
                    "Transaction Remarks": row.iloc[5],
                    "Withdrawal Amount (INR )": row.iloc[6] if pd.notna(row.iloc[6]) else 0.0,
                    "Deposit Amount (INR )": row.iloc[7] if pd.notna(row.iloc[7]) else 0.0,
                    "Balance (INR )": row.iloc[8]
                }
                
                record = BankStatementRecord(**record_data)
                validated_records.append(record)
                
            except ValidationError as e:
                validation_errors.append(f"Row {i}: {e}")
            except Exception as e:
                validation_errors.append(f"Row {i}: Unexpected error - {e}")
        
        if validation_errors:
            logger.warning(f"Bank statement validation errors: {len(validation_errors)}")
            for error in validation_errors[:5]:  # Show first 5 errors
                logger.warning(f"  {error}")
                
        logger.info(f"Validated {len(validated_records)} bank statement records, {len(validation_errors)} errors")
        return validated_records
