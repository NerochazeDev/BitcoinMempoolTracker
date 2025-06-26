"""
Automatic Transaction Replacer - Automatically replace transactions to a target address
"""

import time
import json
import logging
from typing import Dict, Optional, Set
from mempool_monitor import MempoolMonitor
from transaction_replacer import TransactionReplacer
from display_manager import DisplayManager
from config import Config
import requests

class AutoReplacer:
    """Automatically replace detected RBF transactions to a target address"""
    
    def __init__(self, target_address: str, replacement_strategy: str = 'moderate'):
        self.target_address = target_address
        self.replacement_strategy = replacement_strategy
        self.logger = logging.getLogger(__name__)
        self.display = DisplayManager()
        self.config = Config()
        self.replacer = TransactionReplacer()
        
        # Track processed transactions to avoid duplicates
        self.processed_txids: Set[str] = set()
        self.replacement_count = 0
        
        # Session for API calls
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Bitcoin-AutoReplacer/1.0'
        })
        
    def validate_target_address(self) -> bool:
        """Validate the target Bitcoin address format"""
        if not self.target_address:
            return False
            
        # Basic validation - Bitcoin addresses start with 1, 3, or bc1
        if len(self.target_address) < 26 or len(self.target_address) > 62:
            return False
            
        if not (self.target_address.startswith('1') or 
                self.target_address.startswith('3') or 
                self.target_address.startswith('bc1')):
            return False
            
        return True
    
    def get_transaction_details(self, txid: str) -> Optional[Dict]:
        """Fetch transaction details from API"""
        try:
            url = f"{self.config.get_api_url()}/tx/{txid}"
            response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API error {response.status_code} for txid {txid}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching transaction {txid}: {e}")
            return None
    
    def create_replacement_to_address(self, tx_data: Dict) -> Optional[Dict]:
        """Create a replacement transaction that sends outputs to target address"""
        try:
            txid = tx_data.get('txid', '')
            
            # Check if transaction can be replaced
            analysis = self.replacer.analyze_replacement_potential(tx_data)
            if not analysis['can_replace']:
                self.logger.info(f"Transaction {txid} cannot be replaced: {analysis['reason']}")
                return None
            
            # Calculate new fee
            strategies = analysis['replacement_strategies']
            selected_strategy = None
            for strategy in strategies:
                if strategy['name'] == self.replacement_strategy:
                    selected_strategy = strategy
                    break
            
            if not selected_strategy:
                self.logger.error(f"Strategy {self.replacement_strategy} not found")
                return None
            
            # Create custom replacement that sends to our address
            new_tx = self._build_custom_replacement(tx_data, selected_strategy, analysis)
            
            return {
                'success': True,
                'original_txid': txid,
                'replacement_transaction': new_tx,
                'strategy_used': selected_strategy,
                'target_address': self.target_address,
                'total_value_redirected': self._calculate_redirected_value(new_tx),
                'fee_increase': selected_strategy['fee_increase']
            }
            
        except Exception as e:
            self.logger.error(f"Error creating replacement for {tx_data.get('txid', 'unknown')}: {e}")
            return None
    
    def _build_custom_replacement(self, original_tx: Dict, strategy: Dict, analysis: Dict) -> Dict:
        """Build replacement transaction that redirects outputs to target address"""
        new_tx = {
            'version': original_tx.get('version', 1),
            'locktime': original_tx.get('locktime', 0),
            'vin': [],
            'vout': []
        }
        
        # Copy inputs with RBF signaling
        for inp in original_tx.get('vin', []):
            new_input = inp.copy()
            new_input['sequence'] = min(inp.get('sequence', 0xffffffff), 0xfffffffd)
            new_tx['vin'].append(new_input)
        
        # Calculate total input value
        total_input_value = 0
        for inp in original_tx.get('vin', []):
            if 'prevout' in inp and 'value' in inp['prevout']:
                total_input_value += inp['prevout']['value']
        
        # Calculate new fee
        new_fee = analysis['current_fee'] + strategy['fee_increase']
        
        # Create single output to target address with remaining value
        remaining_value = total_input_value - new_fee
        
        if remaining_value > 546:  # Above dust limit
            new_tx['vout'].append({
                'value': remaining_value,
                'scriptpubkey_address': self.target_address,
                'scriptpubkey_type': self._get_script_type(self.target_address),
                'note': f'Auto-replacement redirect to {self.target_address}'
            })
        
        return new_tx
    
    def _get_script_type(self, address: str) -> str:
        """Determine script type from address"""
        if address.startswith('1'):
            return 'p2pkh'
        elif address.startswith('3'):
            return 'p2sh'
        elif address.startswith('bc1'):
            return 'v0_p2wpkh' if len(address) == 42 else 'v1_p2tr'
        return 'unknown'
    
    def _calculate_redirected_value(self, tx: Dict) -> int:
        """Calculate total value being redirected"""
        total = 0
        for output in tx.get('vout', []):
            total += output.get('value', 0)
        return total
    
    def process_rbf_transaction(self, txid: str) -> bool:
        """Process a single RBF transaction for replacement"""
        if txid in self.processed_txids:
            return False
        
        self.processed_txids.add(txid)
        
        # Fetch transaction details
        tx_data = self.get_transaction_details(txid)
        if not tx_data:
            return False
        
        # Create replacement
        replacement = self.create_replacement_to_address(tx_data)
        if not replacement:
            return False
        
        # Save replacement data
        filename = f"auto_replacement_{txid[:16]}_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(replacement, f, indent=2)
        
        # Display results
        self.display_replacement_created(replacement, filename)
        self.replacement_count += 1
        
        return True
    
    def display_replacement_created(self, replacement: Dict, filename: str):
        """Display replacement creation results"""
        print("\n" + "="*60)
        print("🔄 AUTOMATIC REPLACEMENT CREATED")
        print("="*60)
        print(f"Original TxID: {replacement['original_txid'][:16]}...")
        print(f"Target Address: {replacement['target_address']}")
        print(f"Strategy: {replacement['strategy_used']['name'].upper()}")
        print(f"Redirected Value: {replacement['total_value_redirected']} sat")
        print(f"Fee Increase: +{replacement['fee_increase']} sat")
        print(f"New Fee Rate: {replacement['strategy_used']['new_fee_rate']:.2f} sat/vB")
        print(f"Saved to: {filename}")
        print("="*60)
        print("⚠️  WARNING: Replacement created but NOT signed or broadcast")
        print("⚠️  This is for testing replacement creation only")
        print()
    
    def monitor_and_replace(self, duration_minutes: int = 60):
        """Monitor mempool and automatically create replacements"""
        if not self.validate_target_address():
            print(f"❌ Invalid target address: {self.target_address}")
            return
        
        print(f"🔄 Starting Auto-Replacer")
        print(f"Target Address: {self.target_address}")
        print(f"Strategy: {self.replacement_strategy}")
        print(f"Duration: {duration_minutes} minutes")
        print("="*60)
        
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
                    for txid in new_txids:
                        if len(new_txids) > 100:  # Avoid processing too many at once
                            break
                            
                        # Quick check if it's RBF
                        tx_data = self.get_transaction_details(txid)
                        if tx_data and self._is_rbf_transaction(tx_data):
                            print(f"🎯 Found RBF transaction: {txid[:16]}...")
                            self.process_rbf_transaction(txid)
                    
                    known_txids = current_txids
                    
                    # Show status
                    elapsed = int((time.time() - start_time) / 60)
                    remaining = duration_minutes - elapsed
                    print(f"⏱️  Running: {elapsed}m elapsed, {remaining}m remaining, {self.replacement_count} replacements created")
                
            except Exception as e:
                self.logger.error(f"Error in monitoring cycle: {e}")
            
            time.sleep(10)  # Check every 10 seconds
        
        print(f"\n✅ Auto-Replacer completed: {self.replacement_count} replacements created")
    
    def _is_rbf_transaction(self, tx_data: Dict) -> bool:
        """Quick check if transaction signals RBF"""
        for inp in tx_data.get('vin', []):
            if inp.get('sequence', 0xffffffff) < 0xfffffffe:
                return True
        return False

def main():
    """Main entry point for auto-replacer"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python auto_replacer.py <target_address> [strategy] [duration_minutes]")
        print("Example: python auto_replacer.py 1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9 moderate 30")
        return
    
    target_address = sys.argv[1]
    strategy = sys.argv[2] if len(sys.argv) > 2 else 'moderate'
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    
    replacer = AutoReplacer(target_address, strategy)
    replacer.monitor_and_replace(duration)

if __name__ == "__main__":
    main()