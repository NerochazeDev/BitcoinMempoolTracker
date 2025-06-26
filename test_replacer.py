#!/usr/bin/env python3
"""
Test Replacer - Quick test with current RBF transactions
"""

import sys
from auto_replacer import AutoReplacer

def test_with_current_transactions():
    """Test replacement with transactions from your monitor"""
    
    # Your target address
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    
    print("Testing automatic replacement to your address:")
    print(f"Target: {target_address}")
    print()
    
    # Recent transactions from your monitor
    test_transactions = [
        "91fdc275dac43728628dfcf5adc796044247d68e5aebfcf4c5e7c847bc032ab7",
        "4881b8aadffb523170eee222ce04392cca8ea156e9bdbf92c9e0060392c46b00",
        "4931ffa8b9c159a0d93a026c9b5f0f17d822f598acfbda44439f3cdd5b97b47b"
    ]
    
    replacer = AutoReplacer(target_address, 'moderate')
    
    for i, txid in enumerate(test_transactions, 1):
        print(f"[{i}/{len(test_transactions)}] Testing transaction: {txid[:16]}...")
        
        success = replacer.process_rbf_transaction(txid)
        if success:
            print("✅ Replacement created successfully")
        else:
            print("❌ Could not create replacement")
        print()
    
    print(f"Test completed. {replacer.replacement_count} replacements created.")
    print("Check the generated JSON files for replacement details.")

if __name__ == "__main__":
    test_with_current_transactions()