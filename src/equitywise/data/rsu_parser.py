"""
RSU PDF Parser for RSU vesting data extraction.
Extracts vesting events with FMV and exchange rates directly from RSU statements.
"""

import pdfplumber
import pandas as pd
import re
from datetime import datetime, date as Date
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from loguru import logger


class RSUVestingRecord(BaseModel):
    """Model for RSU vesting data extracted from PDF"""
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
        """Parse vesting date from various formats"""
        if isinstance(v, Date):
            return v
        if isinstance(v, str):
            # Handle various date formats
            for date_format in ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d']:
                try:
                    return datetime.strptime(v, date_format).date()
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {v}")
        raise ValueError(f"Invalid date format: {v}")

    @field_validator('quantity', 'wh_quantity', mode='before')
    @classmethod
    def parse_quantity(cls, v):
        """Parse quantity, handling potential string values"""
        if isinstance(v, str):
            return int(float(v.replace(',', '')))
        return int(v)

    @field_validator('fmv_usd', 'total_usd', 'forex_rate', 'total_inr', 'wh_fmv_usd', 'wh_total_inr', mode='before')
    @classmethod
    def parse_currency(cls, v):
        """Parse currency values, handling commas and currency symbols"""
        if isinstance(v, str):
            # Remove currency symbols and commas
            cleaned = v.replace('$', '').replace(',', '').replace('₹', '').strip()
            return float(cleaned)
        return float(v)

    def __str__(self):
        """String representation with key details"""
        return f"RSU Vesting: {self.grant_number} | {self.quantity} shares | {self.vesting_date} | ${self.fmv_usd:.2f} | ₹{self.total_inr:,.2f}"

    def __repr__(self):
        """Detailed representation for debugging"""
        return f"RSUVestingRecord(grant_number='{self.grant_number}', quantity={self.quantity}, vesting_date={self.vesting_date}, fmv_usd={self.fmv_usd}, total_inr={self.total_inr})"

    def dict(self, *args, **kwargs):
        """Override dict to format dates properly"""
        d = super().model_dump(*args, **kwargs)
        if 'vesting_date' in d:
            d['vesting_date'] = self.vesting_date.strftime('%Y-%m-%d')
        return d

    def model_dump_json(self, *args, **kwargs):
        """Override JSON serialization to handle dates"""
        return super().model_dump_json(*args, **kwargs, default=str)

    def to_dict(self):
        """Convert to dictionary with formatted values for export"""
        return {
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'grant_number': self.grant_number,
            'grant_type': self.grant_type,
            'quantity': self.quantity,
            'vesting_date': self.vesting_date.strftime('%Y-%m-%d'),
            'fmv_usd': round(self.fmv_usd, 4),
            'total_usd': round(self.total_usd, 2),
            'forex_rate': round(self.forex_rate, 4),
            'total_inr': round(self.total_inr, 2),
            'wh_quantity': self.wh_quantity,
            'wh_fmv_usd': round(self.wh_fmv_usd, 4),
            'wh_total_inr': round(self.wh_total_inr, 2)
        }

    def __str__(self):
        """String representation with formatted date"""
        return f"employee_id='{self.employee_id}' employee_name='{self.employee_name}' grant_number='{self.grant_number}' grant_type='{self.grant_type}' quantity={self.quantity} vesting_date={self.vesting_date.strftime('%Y-%m-%d')} fmv_usd={self.fmv_usd} total_usd={self.total_usd} forex_rate={self.forex_rate} total_inr={self.total_inr} wh_quantity={self.wh_quantity} wh_fmv_usd={self.wh_fmv_usd} wh_total_inr={self.wh_total_inr}"


class RSUParser:
    """Parser for RSU PDF files containing RSU vesting data"""
    
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
        """Parse a single RSU line from the PDF text using simple split approach"""
        try:
            # Use simple split approach since regex is complex
            # Format: RSU RU403833 $0.00 2 NA 15-01-2025 $419.49 $838.98 86.3632 72457 0 $419.49 86.3632 $0.00 0 72,457.00
            
            if not line.startswith('RSU '):
                return None
                
            parts = line.split()
            if len(parts) < 16:  # Need at least 16 parts for a complete RSU record
                logger.debug(f"Insufficient parts in RSU line: {len(parts)} parts")
                return None
            
            # Extract fields by position
            grant_number = parts[1]          # RU403833
            quantity = int(parts[3])         # 2
            date_str = parts[5]              # 15-01-2025
            fmv_usd_str = parts[6][1:]       # $419.49 -> 419.49
            total_usd_str = parts[7][1:]     # $838.98 -> 838.98
            forex_rate = float(parts[8])     # 86.3632
            total_inr_str = parts[9]         # 72457
            wh_quantity = int(float(parts[10]))  # 0.00 -> 0.0 -> 0
            wh_fmv_usd_str = parts[11][1:]   # $419.49 -> 419.49
            
            # Parse date with flexible format
            if '/' in date_str:
                vesting_date = datetime.strptime(date_str, '%d/%m/%Y').date()
            else:
                vesting_date = datetime.strptime(date_str, '%d-%m-%Y').date()
            
            # Parse numeric fields
            fmv_usd = float(fmv_usd_str)
            total_usd = float(total_usd_str.replace(',', ''))
            total_inr = float(total_inr_str.replace(',', ''))
            wh_fmv_usd = float(wh_fmv_usd_str)
            
            # Calculate withholding total INR based on proportion
            wh_total_inr = total_inr * (wh_quantity / quantity) if wh_quantity > 0 else 0.0
            
            return {
                'grant_number': grant_number,
                'grant_type': 'RSU',
                'quantity': quantity,
                'vesting_date': vesting_date,
                'fmv_usd': fmv_usd,
                'total_usd': total_usd,
                'forex_rate': forex_rate,
                'total_inr': total_inr,
                'wh_quantity': wh_quantity,
                'wh_fmv_usd': wh_fmv_usd,
                'wh_total_inr': wh_total_inr
            }
            
        except Exception as e:
            logger.warning(f"Could not parse RSU line: {line[:100]}... Error: {e}")
            return None
    
    def extract_vesting_data(self) -> List[RSUVestingRecord]:
        """Extract all vesting records from the RSU PDF"""
        logger.info(f"Parsing RSU PDF: {self.pdf_path}")
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"RSU PDF not found: {self.pdf_path}")
        
        records = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                    
                # Extract employee info from first page
                if not self.employee_info:
                    self.employee_info = self._extract_employee_info(text)
                
                # Process each line looking for RSU records
                for line in text.split('\n'):
                    if 'RSU' in line and '$' in line:
                        parsed_data = self._parse_rsu_line(line)
                        if parsed_data:
                            # Add employee info
                            parsed_data.update(self.employee_info)
                            
                            try:
                                record = RSUVestingRecord(**parsed_data)
                                records.append(record)
                                logger.debug(f"Parsed vesting: {record.grant_number} - {record.quantity} shares on {record.vesting_date}")
                            except Exception as e:
                                logger.error(f"Failed to create RSUVestingRecord: {e}")
                                continue
        
        logger.info(f"Successfully parsed {len(records)} vesting records from RSU PDF")
        return records
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert extracted vesting data to pandas DataFrame"""
        records = self.extract_vesting_data()
        if not records:
            return pd.DataFrame()
        
        # Convert to dictionaries for DataFrame
        data = [record.to_dict() for record in records]
        df = pd.DataFrame(data)
        
        # Ensure proper data types
        df['vesting_date'] = pd.to_datetime(df['vesting_date']).dt.date
        df['quantity'] = df['quantity'].astype(int)
        df['wh_quantity'] = df['wh_quantity'].astype(int)
        
        # Round financial columns
        financial_cols = ['fmv_usd', 'total_usd', 'forex_rate', 'total_inr', 'wh_fmv_usd', 'wh_total_inr']
        for col in financial_cols:
            if col in df.columns:
                df[col] = df[col].round(4)
        
        return df
    
    def save_to_csv(self, output_path: str) -> None:
        """Save extracted data to CSV file for backup/inspection"""
        df = self.to_dataframe()
        df.to_csv(output_path, index=False)
        logger.info(f"RSU vesting data saved to: {output_path}")


def parse_rsu_pdf(pdf_path: str) -> List[RSUVestingRecord]:
    """Convenience function to parse RSU PDF and return vesting records"""
    parser = RSUParser(pdf_path)
    return parser.extract_vesting_data()
