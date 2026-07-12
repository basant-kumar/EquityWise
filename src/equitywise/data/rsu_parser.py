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
    """Model for RSU/ESPP equity data extracted from PDF"""
    employee_id: str
    employee_name: str
    grant_number: str
    grant_type: str = "RSU"  # RSU or ESPP
    quantity: float
    vesting_date: Date  # For ESPP, this is the purchase date
    fmv_usd: float = Field(description="Fair Market Value per share in USD")
    total_usd: float = Field(description="Total value in USD (vesting for RSU, purchase for ESPP)")
    forex_rate: float = Field(description="USD to INR exchange rate")
    total_inr: float = Field(description="Total value in INR")
    wh_quantity: float = Field(default=0.0, description="Withholding quantity")
    wh_fmv_usd: float = Field(default=0.0, description="Withholding FMV USD")
    wh_total_inr: float = Field(default=0.0, description="Withholding total INR")
    grant_price_usd: Optional[float] = Field(default=None, description="Grant/purchase price per share (for ESPP)")

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
        """Parse quantity as float so ESPP fractional purchases (e.g. 19.15) survive."""
        if isinstance(v, str):
            return float(v.replace(',', ''))
        return float(v)

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
    
    def _parse_equity_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single RSU or ESPP line from the PDF text using flexible field detection"""
        try:
            # Handle variable RSU and ESPP line formats with smart field detection
            # RSU Format variations:
            # Standard:  RSU RU403833 $0.00 2 15-01-2025 $419.49 $838.98 86.3632 72457 0 $419.49 86.3632 $0.00 0 72,457.00
            # With NA:   RSU RU325284 $ 0 37 NA 15-04-2020 $ 333.95 $ 12356.15 76.498 945221 16 $ 333.95 76.498 $ 5343.2 4087...
            # 
            # ESPP Format variations:
            # Standard:  ESPP 03 $ 255.8245 14 NA 31-12-2019 $ 328.03 $ 1010.877 71.274 72049 0 $ 328.03 71.274 $ 0 0 72049
            # Attached:  ESPP 2020 $255.8245 16 NA 30-06-2020 $430.995 $2802.728 75.527 211682 0 $430.995 75.527 $0 0 211682
            
            # Check if this is an RSU or ESPP line
            equity_type = None
            if line.startswith('RSU '):
                equity_type = "RSU"
            elif line.startswith('ESPP '):
                equity_type = "ESPP"
            else:
                return None
                
            parts = line.split()
            if len(parts) < 15:  # Need at least 15 parts for a complete equity record
                logger.debug(f"Insufficient parts in {equity_type} line: {len(parts)} parts")
                return None
            
            # Extract basic fields (different for RSU vs ESPP)
            if equity_type == "RSU":
                grant_number = parts[1]      # RU403833, RU325284, etc.
                grant_price_usd = None       # RSU has no purchase price
            else:  # ESPP
                grant_number = parts[1]      # Plan identifier like "03", "2020"
                # Extract grant price - look for first $ value after plan identifier
                grant_price_usd = None
                for i in range(2, min(6, len(parts))):
                    if parts[i].startswith('$'):
                        try:
                            grant_price_usd = float(parts[i][1:])
                            break
                        except ValueError:
                            continue
                    elif parts[i] not in ['$', 'NA'] and '.' in parts[i]:
                        try:
                            grant_price_usd = float(parts[i])
                            break
                        except ValueError:
                            continue
            
            # Smart detection for quantity and date fields
            # Look for the date field by pattern matching instead of fixed position
            date_str = None
            date_index = None
            
            # Search for date pattern in positions 5-7 (common variations)
            for i in range(5, min(8, len(parts))):
                candidate = parts[i]
                # Check if this looks like a date (contains digits and dashes/slashes)
                if re.match(r'\d{1,2}[-/]\w{2,3}[-/]\d{2,4}', candidate):
                    date_str = candidate
                    date_index = i
                    break
                    
            if not date_str or date_index is None:
                logger.debug(f"Could not find date field in RSU line: {parts}")
                return None
                
            # Extract quantity - find the LAST numeric field before the date
            # This handles cases where there are multiple numbers (like grant price, then quantity)
            quantity = None
            for i in range(date_index - 1, 1, -1):  # Search backwards from date
                candidate = parts[i]
                # Skip "NA" and "$" values
                if candidate in ['NA', '$', '']:
                    continue
                    
                try:
                    # Try to parse as float first, then convert to int
                    float_val = float(candidate.replace(',', '').replace('$', ''))
                    if float_val > 0:  # Skip zero values
                        quantity = float_val
                        break
                except (ValueError, AttributeError):
                    continue
                    
            if quantity is None:
                logger.debug(f"Could not find valid quantity in RSU line: {parts}")
                return None
                
            # Extract financial fields after date - handle both $ formats
            # Format 1: $ 333.95 $ 12356.15 ($ as separate tokens)
            # Format 2: $472.47 $3,779.76 ($ attached to numbers)
            base_idx = date_index + 1  # Start after date field
            
            def get_usd_value(idx):
                """Extract USD value, handling both $ formats"""
                if idx >= len(parts):
                    return None, idx
                
                part = parts[idx]
                if part == '$':
                    # Format 1: $ as separate token
                    idx += 1
                    if idx >= len(parts):
                        return None, idx
                    value = float(parts[idx].replace(',', ''))
                    return value, idx + 1
                elif part.startswith('$'):
                    # Format 2: $ attached to number
                    value = float(part[1:].replace(',', ''))
                    return value, idx + 1
                else:
                    # No $ prefix, treat as direct number
                    value = float(part.replace(',', ''))
                    return value, idx + 1
            
            # Get FMV USD value
            fmv_usd, base_idx = get_usd_value(base_idx)
            if fmv_usd is None:
                logger.debug(f"Could not extract FMV USD from RSU line")
                return None
            
            # Get Total USD value
            total_usd, base_idx = get_usd_value(base_idx)
            if total_usd is None:
                logger.debug(f"Could not extract Total USD from RSU line")
                return None
            
            # Get forex rate and total INR
            if base_idx >= len(parts):
                logger.debug(f"Missing forex rate in RSU line")
                return None
            forex_rate = float(parts[base_idx])
            base_idx += 1
            
            if base_idx >= len(parts):
                logger.debug(f"Missing total INR in RSU line")
                return None
            total_inr = float(parts[base_idx].replace(',', ''))
            base_idx += 1
            
            # Get withholding quantity
            if base_idx >= len(parts):
                logger.debug(f"Missing withholding quantity in RSU line")
                return None
            wh_quantity = float(parts[base_idx])
            base_idx += 1
            
            # Get withholding FMV USD
            wh_fmv_usd, base_idx = get_usd_value(base_idx)
            if wh_fmv_usd is None:
                logger.debug(f"Could not extract withholding FMV USD from RSU line")
                return None
            
            # Skip forex rate for withholding (usually same as main)
            base_idx += 1  # Skip withholding forex rate
            
            # Parse date with flexible format handling multiple variations
            vesting_date = None
            date_formats = [
                '%d-%m-%Y',     # 15-04-2020 (DD-MM-YYYY)
                '%d/%m/%Y',     # 15/04/2020 (DD/MM/YYYY)
                '%m/%d/%Y',     # 12/29/2023 (MM/DD/YYYY) - American format
                '%d-%b-%y',     # 15-Oct-20 (DD-Mon-YY)
                '%d-%B-%y',     # 15-October-20 (DD-Month-YY)
                '%d/%b/%Y',     # 15/Oct/2020 (DD/Mon/YYYY)
                '%d-%m-%y',     # 15-04-20 (DD-MM-YY)
                '%m-%d-%Y',     # 12-29-2023 (MM-DD-YYYY) - American format with dashes
                '%Y-%m-%d'      # 2023-12-29 (YYYY-MM-DD) - ISO format
            ]
            
            for date_format in date_formats:
                try:
                    vesting_date = datetime.strptime(date_str, date_format).date()
                    break
                except ValueError:
                    continue
                    
            if vesting_date is None:
                logger.debug(f"Could not parse date '{date_str}' with any known format")
                return None
            
            # Calculate withholding total INR based on proportion
            wh_total_inr = total_inr * (wh_quantity / quantity) if wh_quantity > 0 else 0.0
            
            return {
                'grant_number': grant_number,
                'grant_type': equity_type,
                'quantity': quantity,
                'vesting_date': vesting_date,
                'fmv_usd': fmv_usd,
                'total_usd': total_usd,
                'forex_rate': forex_rate,
                'total_inr': total_inr,
                'wh_quantity': wh_quantity,
                'wh_fmv_usd': wh_fmv_usd,
                'wh_total_inr': wh_total_inr,
                'grant_price_usd': grant_price_usd
            }
            
        except Exception as e:
            logger.warning(f"Could not parse {equity_type if 'equity_type' in locals() else 'equity'} line: {line[:100]}... Error: {e}")
            return None
    
    def extract_vesting_data(self) -> List[RSUVestingRecord]:
        """Extract all RSU and ESPP equity records from the source file.

        Accepts either a PDF (Excelity Stock Perquisites Statement) or an
        XLSX/XLS with the same column layout — some Adobe portals disable
        the PDF download but still allow spreadsheet export.
        """
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"RSU statement not found: {self.pdf_path}")

        suffix = self.pdf_path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            return self._extract_from_xlsx()

        logger.info(f"Parsing RSU/ESPP PDF: {self.pdf_path}")

        records = []
        all_text = ""  # Collect all text for validation

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                all_text += text + "\n"  # Accumulate text for validation
                    
                # Extract employee info from first page
                if not self.employee_info:
                    self.employee_info = self._extract_employee_info(text)
                
                # Process each line looking for RSU and ESPP records
                for line in text.split('\n'):
                    if ('RSU' in line or 'ESPP' in line) and '$' in line:
                        parsed_data = self._parse_equity_line(line)
                        if parsed_data:
                            # Add employee info
                            parsed_data.update(self.employee_info)
                            
                            try:
                                record = RSUVestingRecord(**parsed_data)
                                records.append(record)
                                equity_type = parsed_data.get('grant_type', 'equity')
                                logger.debug(f"Parsed {equity_type}: {record.grant_number} - {record.quantity} shares on {record.vesting_date}")
                            except Exception as e:
                                logger.error(f"Failed to create equity record: {e}")
                                continue
        
        logger.info(f"Successfully parsed {len(records)} equity records from PDF")
        
        # Validation: Check if we missed any entries
        self._validate_parsing_completeness(all_text, len(records))
        
        return records
    
    def _validate_parsing_completeness(self, pdf_text: str, parsed_count: int) -> None:
        """Validate that we haven't missed any RSU/ESPP entries during parsing"""
        lines = pdf_text.split('\n')
        expected_equity_lines = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith('RSU ') or line.startswith('ESPP '):
                expected_equity_lines.append((line_num, line[:100] + '...' if len(line) > 100 else line))
        
        expected_count = len(expected_equity_lines)
        
        if parsed_count != expected_count:
            logger.warning(f"⚠️  PARSING MISMATCH: Expected {expected_count} entries, but parsed {parsed_count}")
            logger.warning(f"📊 Expected equity lines found in PDF:")
            for line_num, line_preview in expected_equity_lines:
                logger.warning(f"   Line {line_num}: {line_preview}")
            
            missing_count = expected_count - parsed_count
            if missing_count > 0:
                logger.error(f"❌ {missing_count} entries were NOT parsed successfully!")
                logger.error(f"💡 This indicates parsing logic needs improvement for this PDF format")
        else:
            logger.info(f"✅ Parsing validation passed: {parsed_count}/{expected_count} entries parsed successfully")
    
    # ------------------------------------------------------------------
    # XLSX / XLS input path
    # ------------------------------------------------------------------
    # Column layout mirrors Excelity's Stock Perquisites Statement:
    #   Type of Plan | Grant Number/Plan Number | Grant Price in USD $ |
    #   Quantity | Excercise Date(For ESOP Only) | Vesting/Purchase Date |
    #   FMV in USD $ | Total Perquisites in USD $ | Forex rates in USD $ |
    #   Total Perquisites in INR | Equity WH (QTY) | FMV (WH) |
    #   Forex Rate (WH) | WH Perquisites in USD | Perq on Equity WH in (INR) |
    #   Total Perquisites on form 16 (INR)
    _XLSX_COL_MAP = {
        "type_of_plan": ["type of plan", "plan type"],
        "grant_number": ["grant number/plan number", "grant number", "plan number"],
        "grant_price": ["grant price in usd $", "grant price in usd", "grant price"],
        "quantity": ["quantity", "qty"],
        "vesting_date": ["vesting/purchase date", "vesting date", "purchase date"],
        "fmv_usd": ["fmv in usd $", "fmv in usd", "fmv"],
        "total_usd": ["total perquisites in usd $", "total perquisites in usd"],
        "forex_rate": ["forex rates in usd $", "forex rate", "forex rates"],
        "total_inr": ["total perquisites in inr"],
        "wh_quantity": ["equity wh (qty)", "wh qty", "equity wh qty"],
        "wh_fmv_usd": ["fmv (wh)", "wh fmv"],
        "wh_total_inr": [
            "perq on equity wh in (inr)",
            "perq on equity wh in inr",
        ],
    }

    def _extract_from_xlsx(self) -> List[RSUVestingRecord]:
        logger.info(f"Parsing RSU/ESPP XLSX: {self.pdf_path}")

        df = pd.read_excel(self.pdf_path)
        df.columns = [str(c).strip() for c in df.columns]
        col_by_lc = {c.lower(): c for c in df.columns}

        def find(field: str) -> str:
            for candidate in self._XLSX_COL_MAP[field]:
                if candidate in col_by_lc:
                    return col_by_lc[candidate]
            raise ValueError(
                f"RSU XLSX {self.pdf_path.name} is missing expected column for '{field}'. "
                f"Looked for any of: {self._XLSX_COL_MAP[field]}. "
                f"Available columns: {list(df.columns)}"
            )

        cols = {field: find(field) for field in self._XLSX_COL_MAP}

        def as_float(v) -> float:
            if pd.isna(v):
                return 0.0
            if isinstance(v, str):
                return float(v.replace("$", "").replace(",", "").strip() or 0)
            return float(v)

        records: List[RSUVestingRecord] = []
        for idx, row in df.iterrows():
            plan_type = str(row[cols["type_of_plan"]]).strip().upper()
            if plan_type not in ("RSU", "ESPP"):
                logger.debug(f"Skipping row {idx}: unknown plan type {plan_type!r}")
                continue

            try:
                quantity = as_float(row[cols["quantity"]])
                total_inr = as_float(row[cols["total_inr"]])
                wh_quantity = as_float(row[cols["wh_quantity"]])
                wh_total_inr = as_float(row[cols["wh_total_inr"]])
                if wh_total_inr == 0.0 and wh_quantity > 0 and quantity > 0:
                    # Preserve the PDF-path's fallback: pro-rate main total INR
                    wh_total_inr = total_inr * (wh_quantity / quantity)

                record = RSUVestingRecord(
                    employee_id=self.employee_info.get("employee_id", "000000"),
                    employee_name=self.employee_info.get("employee_name", "Adobe Employee"),
                    grant_number=str(row[cols["grant_number"]]).strip(),
                    grant_type=plan_type,
                    quantity=quantity,
                    vesting_date=pd.to_datetime(row[cols["vesting_date"]]).date(),
                    fmv_usd=as_float(row[cols["fmv_usd"]]),
                    total_usd=as_float(row[cols["total_usd"]]),
                    forex_rate=as_float(row[cols["forex_rate"]]),
                    total_inr=total_inr,
                    wh_quantity=wh_quantity,
                    wh_fmv_usd=as_float(row[cols["wh_fmv_usd"]]),
                    wh_total_inr=wh_total_inr,
                    grant_price_usd=as_float(row[cols["grant_price"]]) if plan_type == "ESPP" else None,
                )
                records.append(record)
                logger.debug(
                    f"Parsed {plan_type}: {record.grant_number} - "
                    f"{record.quantity} shares on {record.vesting_date}"
                )
            except Exception as e:
                logger.warning(f"Row {idx} in {self.pdf_path.name}: could not parse — {e}")
                continue

        logger.info(f"Successfully parsed {len(records)} equity records from XLSX")
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
        df['quantity'] = df['quantity'].astype(float)
        df['wh_quantity'] = df['wh_quantity'].astype(float)
        
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
