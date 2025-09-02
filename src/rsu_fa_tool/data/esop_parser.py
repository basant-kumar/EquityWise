"""
ESOP PDF Parser for RSU vesting data extraction.
Extracts vesting events with FMV and exchange rates directly from ESOP statements.
"""

import pdfplumber
import pandas as pd
import re
from datetime import datetime, date as Date
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from loguru import logger


class ESOPVestingRecord(BaseModel):
    """Model for ESOP vesting data extracted from PDF"""
    employee_id: str
    employee_name: str
    grant_number: str
    grant_type: str = "RSU"  # Usually RSU
    quantity: int
    vesting_date: Date
    fmv_usd: float = Field(description="Fair Market Value per share in USD")
    total_usd: float = Field(description="Total vesting value in USD")
    forex_rate: float = Field(description="USD to INR exchange rate")
    total_inr: float = Field(description="Total vesting value in INR")
    wh_quantity: int = Field(default=0, description="Withholding quantity")
    wh_fmv_usd: float = Field(default=0.0, description="Withholding FMV USD")
    wh_total_inr: float = Field(default=0.0, description="Withholding total INR")
    
    @field_validator('vesting_date', mode='before')
    @classmethod
    def parse_vesting_date(cls, v):
        """Parse vesting date from DD-MM-YYYY format"""
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%d-%m-%Y').date()
            except ValueError:
                # Try alternative formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        return datetime.strptime(v, fmt).date()
                    except ValueError:
                        continue
                raise ValueError(f"Could not parse date: {v}")
        return v
    
    @field_validator('fmv_usd', 'total_usd', 'wh_fmv_usd', mode='before')
    @classmethod
    def parse_currency(cls, v):
        """Parse currency values, removing $ signs"""
        if isinstance(v, str):
            # Remove $ and commas, convert to float
            cleaned = v.replace('$', '').replace(',', '').strip()
            return float(cleaned) if cleaned else 0.0
        return float(v) if v is not None else 0.0
    
    @field_validator('total_inr', 'wh_total_inr', mode='before')
    @classmethod
    def parse_inr_currency(cls, v):
        """Parse INR values, removing commas"""
        if isinstance(v, str):
            # Remove commas and convert to float
            cleaned = v.replace(',', '').strip()
            return float(cleaned) if cleaned else 0.0
        return float(v) if v is not None else 0.0
    
    @field_validator('fmv_usd', 'total_usd', mode='after')
    @classmethod
    def validate_positive_usd_values(cls, v):
        """Validate USD values are positive"""
        if v is not None and v < 0:
            raise ValueError("USD values must be positive")
        return v
    
    @field_validator('quantity', mode='after')
    @classmethod
    def validate_positive_quantity(cls, v):
        """Validate quantity is positive"""
        if v is not None and v <= 0:
            raise ValueError("Quantity must be positive")
        return v
    
    @field_validator('forex_rate', mode='after')
    @classmethod
    def validate_positive_forex_rate(cls, v):
        """Validate forex rate is positive"""
        if v is not None and v <= 0:
            raise ValueError("Forex rate must be positive")
        return v
    
    def __str__(self):
        """String representation with formatted date"""
        return f"employee_id='{self.employee_id}' employee_name='{self.employee_name}' grant_number='{self.grant_number}' grant_type='{self.grant_type}' quantity={self.quantity} vesting_date={self.vesting_date.strftime('%Y-%m-%d')} fmv_usd={self.fmv_usd} total_usd={self.total_usd} forex_rate={self.forex_rate} total_inr={self.total_inr} wh_quantity={self.wh_quantity} wh_fmv_usd={self.wh_fmv_usd} wh_total_inr={self.wh_total_inr}"


class ESOPParser:
    """Parser for ESOP PDF files containing RSU vesting data"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.employee_info: Dict[str, str] = {}
        
    def _extract_employee_info(self, text: str) -> Dict[str, str]:
        """Extract employee information from PDF text"""
        info = {}
        
        # Extract employee ID and name from the first line
        employee_line_pattern = r'Employee Id\s+(\d+)\s+Employee Name\s+(.+)'
        match = re.search(employee_line_pattern, text)
        if match:
            info['employee_id'] = match.group(1)
            info['employee_name'] = match.group(2).strip()
            
        return info
    
    def _parse_rsu_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single RSU line from the PDF text"""
        try:
            # More flexible pattern to handle format variations across different years
            # Handles both date formats: 15-01-2025 and 15/11/2023
            # Handles different decimal precision and spacing
            rsu_pattern = (
                r'RSU\s+(RU\d+)\s+\$[\d.]+\s+(\d+)\s+NA\s+'           # RSU grant and quantity
                r'(\d{2}[-/]\d{2}[-/]\d{4})\s+'                       # Date (flexible separator)  
                r'\$([\d.]+)\s+\$([\d,]+\.?\d*)\s+'                   # FMV and Total USD
                r'([\d.]+)\s+([\d,]+\.?\d*)\s+'                       # Exchange rate and Total INR
                r'(\d+)\s+\$([\d.]+)\s+([\d.]+)\s+'                   # WH quantity, WH FMV, WH rate
                r'\$([\d.]+)\s+(\d+)\s+([\d,]+\.?\d*)'                # WH individual values
            )
            
            match = re.search(rsu_pattern, line)
            if not match:
                # Try simpler pattern for older format - just get the core fields we need
                simple_pattern = (
                    r'RSU\s+(RU\d+)\s+\$[\d.]+\s+(\d+)\s+NA\s+'         # RSU grant and quantity
                    r'(\d{2}[-/]\d{2}[-/]\d{4})\s+'                     # Date (flexible separator)
                    r'\$([\d.,]+)\s+\$([\d.,]+)\s+'                     # FMV and Total USD (with commas)
                    r'([\d.,]+)\s+([\d.,]+)'                            # Exchange rate and Total INR (with commas)
                )
                
                simple_match = re.search(simple_pattern, line)
                if simple_match:
                    # For older format, set defaults for missing WH fields
                    return {
                        'grant_number': simple_match.group(1),
                        'quantity': int(simple_match.group(2)),
                        'vesting_date': simple_match.group(3).replace('/', '-'),  # Normalize date format
                        'fmv_usd': simple_match.group(4).replace(',', ''),
                        'total_usd': simple_match.group(5).replace(',', ''),
                        'forex_rate': float(simple_match.group(6).replace(',', '')),
                        'total_inr': simple_match.group(7).replace(',', ''),
                        'wh_quantity': 0,
                        'wh_fmv_usd': "0.00",
                        'wh_forex_rate': float(simple_match.group(6).replace(',', '')),  # Same as main rate
                        'wh_fmv_individual': "0.00",
                        'wh_total_inr_individual': 0,
                        'wh_total_inr': "0.00"
                    }
                
                return None
                
            # Successful primary pattern match
            return {
                'grant_number': match.group(1),
                'quantity': int(match.group(2)),
                'vesting_date': match.group(3).replace('/', '-'),  # Normalize date format
                'fmv_usd': match.group(4),
                'total_usd': match.group(5).replace(',', ''),
                'forex_rate': float(match.group(6)),
                'total_inr': match.group(7).replace(',', ''),
                'wh_quantity': int(match.group(8)),
                'wh_fmv_usd': match.group(9),
                'wh_forex_rate': float(match.group(10)),
                'wh_fmv_individual': match.group(11),
                'wh_total_inr_individual': int(match.group(12)),
                'wh_total_inr': match.group(13).replace(',', '')
            }
            
        except Exception as e:
            logger.warning(f"Could not parse RSU line: {line[:100]}... Error: {e}")
            return None
    
    def extract_vesting_data(self) -> List[ESOPVestingRecord]:
        """Extract all vesting records from the ESOP PDF"""
        logger.info(f"Parsing ESOP PDF: {self.pdf_path}")
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"ESOP PDF not found: {self.pdf_path}")
        
        records = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                # Extract employee info from first page
                if not self.employee_info:
                    self.employee_info = self._extract_employee_info(text)
                
                # Extract RSU lines
                lines = text.split('\n')
                
                for line in lines:
                    if line.strip().startswith('RSU'):
                        parsed_data = self._parse_rsu_line(line)
                        if parsed_data:
                            # Add employee info
                            parsed_data.update(self.employee_info)
                            
                            try:
                                record = ESOPVestingRecord(**parsed_data)
                                records.append(record)
                                logger.debug(f"Parsed vesting: {record.grant_number} - {record.quantity} shares on {record.vesting_date}")
                            except Exception as e:
                                logger.error(f"Failed to create ESOPVestingRecord: {e}")
                                continue
        
        logger.info(f"Successfully parsed {len(records)} vesting records from ESOP PDF")
        return records
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert extracted vesting data to pandas DataFrame"""
        records = self.extract_vesting_data()
        if not records:
            return pd.DataFrame()
        
        data = []
        for record in records:
            data.append({
                'employee_id': record.employee_id,
                'employee_name': record.employee_name,
                'grant_number': record.grant_number,
                'grant_type': record.grant_type,
                'quantity': record.quantity,
                'vesting_date': record.vesting_date,
                'fmv_usd': record.fmv_usd,
                'total_usd': record.total_usd,
                'forex_rate': record.forex_rate,
                'total_inr': record.total_inr,
                'wh_quantity': record.wh_quantity,
                'wh_fmv_usd': record.wh_fmv_usd,
                'wh_total_inr': record.wh_total_inr,
            })
        
        return pd.DataFrame(data)
    
    def save_to_csv(self, output_path: str) -> None:
        """Save extracted data to CSV file for backup/inspection"""
        df = self.to_dataframe()
        df.to_csv(output_path, index=False)
        logger.info(f"ESOP vesting data saved to: {output_path}")


def parse_esop_pdf(pdf_path: str) -> List[ESOPVestingRecord]:
    """Convenience function to parse ESOP PDF and return vesting records"""
    parser = ESOPParser(pdf_path)
    return parser.extract_vesting_data()
