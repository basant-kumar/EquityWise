#!/usr/bin/env python3
"""
Test broker transaction detection
"""

from rsu_fa_tool.data.loaders import BankStatementLoader
from rsu_fa_tool.config.settings import settings
from loguru import logger

def test_broker_detection():
    """Test broker transaction detection."""
    logger.info("Testing broker transaction detection...")
    
    for bank_path in settings.bank_statement_paths:
        logger.info(f"\n📊 Testing: {bank_path}")
        try:
            loader = BankStatementLoader(bank_path)
            records = loader.get_validated_records(str(bank_path))
            
            logger.info(f"✅ Successfully loaded {len(records)} records")
            
            # Look for broker transactions
            broker_transactions = []
            for record in records:
                if record.is_broker_transaction:
                    broker_transactions.append(record)
            
            logger.info(f"🔍 Found {len(broker_transactions)} broker transactions")
            
            # Show details of broker transactions
            for i, txn in enumerate(broker_transactions):
                logger.info(f"\nBroker Transaction {i+1}:")
                logger.info(f"  Date: {txn.transaction_date}")
                logger.info(f"  Remarks: {txn.transaction_remarks}")
                logger.info(f"  Amount Received: ₹{txn.deposit_amount:,.2f}")
                
                details = txn.extract_broker_details()
                if details:
                    logger.info(f"  USD Amount: ${details['usd_amount']:,.2f}")
                    logger.info(f"  Exchange Rate: ₹{details['exchange_rate']:.4f}")
                    logger.info(f"  Expected INR: ₹{details['inr_expected']:,.2f}")
                    logger.info(f"  Actual INR: ₹{details['inr_received']:,.2f}")
                    logger.info(f"  Transfer Expense: ₹{details['transfer_expense']:,.2f}")
                    logger.info(f"  Financial Year: {txn.financial_year}")
            
            # Look for transactions containing "IRM" or "USD" for potential missed patterns
            logger.info(f"\n🔍 Looking for potential broker transactions (IRM/USD patterns):")
            potential_broker = []
            for record in records:
                remarks = record.transaction_remarks.upper()
                if ('IRM' in remarks or 'USD' in remarks) and record.is_credit:
                    potential_broker.append(record)
            
            logger.info(f"Found {len(potential_broker)} potential broker transactions")
            for i, txn in enumerate(potential_broker[:5]):  # Show first 5
                logger.info(f"  {i+1}. {txn.transaction_date} | ₹{txn.deposit_amount:,.2f} | {txn.transaction_remarks[:80]}...")
                
        except Exception as e:
            logger.error(f"❌ Error loading {bank_path}: {e}")

if __name__ == "__main__":
    test_broker_detection()
