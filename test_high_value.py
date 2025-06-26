#!/usr/bin/env python3
"""
Test High Value Replacements - Test with actual high-value transactions
"""

from targeted_replacer import TargetedReplacer

def test_with_high_value_transactions():
    """Test replacement with high-value transactions from your monitor"""
    
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    
    # High-value transactions from your monitor (>= 0.0093 BTC)
    high_value_transactions = [
        "4090f7d4c9c6764d10a56d8db3b5ca2e95742b5f61874b9cee9268b2e5c2b6f6",  # 17.96 BTC
        "6fe1fe602adbb201802513298b113c66a30dabbba5b056a4ea65f73009d3207c",  # 0.01386117 BTC
        "e9b5ba6c90d5a164b8c37e203bd631f2f287d0461fc7cb492fde4368ee8ddd79"   # 0.00139016 BTC
    ]
    
    print("Testing targeted replacement for high-value transactions:")
    print(f"Target: {target_address}")
    print(f"Threshold: >= 0.0093 BTC")
    print()
    
    replacer = TargetedReplacer(target_address, 'aggressive')
    
    for i, txid in enumerate(high_value_transactions, 1):
        print(f"[{i}/{len(high_value_transactions)}] Processing: {txid[:16]}...")
        
        success = replacer.process_rbf_transaction(txid)
        if success:
            print("✅ High-value replacement created")
        else:
            print("❌ Could not create replacement")
        print()
    
    print(f"High-value test completed: {replacer.replacement_count} replacements created")

if __name__ == "__main__":
    test_with_high_value_transactions()