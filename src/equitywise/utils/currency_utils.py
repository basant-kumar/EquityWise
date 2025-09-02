"""Currency formatting and calculation utilities for RSU FA Tool.

This module provides utilities for currency formatting and gain/loss calculations.
Currency conversion logic is implemented in the calculators using proper data loaders.
"""

from typing import Dict


def format_currency(amount: float, currency: str = "INR") -> str:
    """Format currency amount with proper symbols and formatting.
    
    Args:
        amount: Amount to format.
        currency: Currency code (INR, USD, etc.).
        
    Returns:
        Formatted currency string.
    """
    if currency == "INR":
        return f"₹{amount:,.2f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def calculate_gain_loss(
    sale_price: float,
    purchase_price: float, 
    currency: str = "USD"
) -> Dict[str, float]:
    """Calculate gain/loss from stock transactions.
    
    Args:
        sale_price: Price at which stock was sold.
        purchase_price: Price at which stock was acquired (FMV at vesting).
        currency: Currency for calculations.
        
    Returns:
        Dictionary with gain/loss information.
    """
    gain_loss = sale_price - purchase_price
    gain_loss_percent = (gain_loss / purchase_price) * 100 if purchase_price > 0 else 0
    
    return {
        "gain_loss_amount": gain_loss,
        "gain_loss_percent": gain_loss_percent,
        "sale_price": sale_price,
        "purchase_price": purchase_price,
        "currency": currency,
        "is_gain": gain_loss > 0
    }
