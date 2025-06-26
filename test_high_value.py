#!/usr/bin/env python3
"""
Test High-Value Replacer - Target $1k+ transactions
"""

from auto_replacer import AutoReplacer

def test_high_value_transactions():
    """Test with high-value transactions from your monitor"""
    
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    
    # High-value transactions detected by your monitor
    high_value_txids = [
        "82b71b78f0f2c0c85bc08c5b94e1f4c9d09407dab40d3e57088f8dd33e54fef1",  # $60,681
        "86c669e2c4b68a63a03ce9dd6284f0a346f2bb1b952b3b6a355dacd190c4d3c1"   # $42,815
    ]
    
    print(f"Testing high-value replacement targeting ${1000}+ transactions")
    print(f"Target address: {target_address}")
    print("="*60)
    
    # Create auto-replacer with $1k minimum
    replacer = AutoReplacer(target_address, 'aggressive', min_value_usd=1000.0)
    
    for i, txid in enumerate(high_value_txids, 1):
        print(f"\n[{i}/{len(high_value_txids)}] Processing: {txid[:16]}...")
        success = replacer.process_rbf_transaction(txid)
        
        if success:
            print("✅ High-value replacement created")
        else:
            print("❌ Could not create replacement")
    
    print(f"\nSummary:")
    print(f"Replacements created: {replacer.replacement_count}")
    print(f"Transactions skipped: {replacer.skipped_count}")

if __name__ == "__main__":
    test_high_value_transactions()