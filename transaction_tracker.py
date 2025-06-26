"""
Transaction Tracker - Track RBF transactions and detect replacements
"""

import time
import logging
from typing import Dict, List, Set, Optional, Callable, Any

class TrackedTransaction:
    """Represents a tracked RBF transaction"""
    
    def __init__(self, txid: str, tx_data: Dict, rbf_info: Dict):
        self.txid = txid
        self.original_data = tx_data
        self.rbf_info = rbf_info
        self.first_seen = time.time()
        self.last_checked = time.time()
        self.replacement_candidates: Set[str] = set()
        self.is_replaced = False
        self.replacement_txid: Optional[str] = None
        
        # Extract input UTXOs for replacement detection
        self.input_utxos = set()
        for vin in tx_data.get('vin', []):
            utxo = f"{vin.get('txid', '')}:{vin.get('vout', 0)}"
            self.input_utxos.add(utxo)
    
    def age_seconds(self) -> float:
        """Get age of transaction in seconds"""
        return time.time() - self.first_seen
    
    def time_since_last_check(self) -> float:
        """Get time since last replacement check"""
        return time.time() - self.last_checked
    
    def update_last_checked(self):
        """Update the last checked timestamp"""
        self.last_checked = time.time()

class TransactionTracker:
    """Track RBF transactions and detect when they are replaced"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.tracked_transactions: Dict[str, TrackedTransaction] = {}
        self.replacement_count = 0
        self.max_tracking_time = 3600  # Stop tracking after 1 hour
        self.cleanup_interval = 300    # Cleanup old transactions every 5 minutes
        self.last_cleanup = time.time()
    
    def add_transaction(self, txid: str, tx_data: Dict, rbf_info: Dict) -> None:
        """Add a new RBF transaction to tracking"""
        if txid not in self.tracked_transactions:
            tracked_tx = TrackedTransaction(txid, tx_data, rbf_info)
            self.tracked_transactions[txid] = tracked_tx
            self.logger.info(f"Started tracking RBF transaction: {txid}")
    
    def remove_transaction(self, txid: str, reason: str = "") -> None:
        """Remove a transaction from tracking"""
        if txid in self.tracked_transactions:
            del self.tracked_transactions[txid]
            self.logger.info(f"Stopped tracking transaction {txid}: {reason}")
    
    def cleanup_old_transactions(self) -> None:
        """Remove old transactions that are unlikely to be replaced"""
        current_time = time.time()
        
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        to_remove = []
        for txid, tracked_tx in self.tracked_transactions.items():
            if tracked_tx.age_seconds() > self.max_tracking_time:
                to_remove.append(txid)
        
        for txid in to_remove:
            self.remove_transaction(txid, "aged out")
        
        self.last_cleanup = current_time
        
        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} old tracked transactions")
    
    def find_potential_replacement(self, tracked_tx: TrackedTransaction, 
                                 tx_fetcher: Callable[[str], Optional[Dict]]) -> Optional[str]:
        """
        Find potential replacement transaction by checking if any new transaction
        spends the same inputs
        """
        try:
            # Check if original transaction still exists in mempool
            current_tx = tx_fetcher(tracked_tx.txid)
            
            # If transaction is no longer in mempool, it might have been replaced or confirmed
            if current_tx is None:
                # Transaction disappeared from mempool
                # This could mean it was replaced or confirmed
                return "DISAPPEARED"
            
            # For a more comprehensive check, we would need to monitor all new transactions
            # that spend the same UTXOs, but that requires more complex mempool analysis
            # For now, we'll detect when a transaction disappears from mempool
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking for replacement of {tracked_tx.txid}: {e}")
            return None
    
    def check_for_replacements(self, tx_fetcher: Callable[[str], Optional[Dict]]) -> List[Dict[str, Any]]:
        """
        Check all tracked transactions for potential replacements
        Returns list of replacement events
        """
        self.cleanup_old_transactions()
        
        replacements = []
        to_remove = []
        
        for txid, tracked_tx in self.tracked_transactions.items():
            try:
                # Skip if checked too recently
                if tracked_tx.time_since_last_check() < 30:  # Check every 30 seconds
                    continue
                
                replacement_status = self.find_potential_replacement(tracked_tx, tx_fetcher)
                tracked_tx.update_last_checked()
                
                if replacement_status == "DISAPPEARED":
                    if not tracked_tx.is_replaced:
                        # Mark as potentially replaced
                        tracked_tx.is_replaced = True
                        
                        replacement_info = {
                            'event_type': 'transaction_disappeared',
                            'original_txid': txid,
                            'original_fee': tracked_tx.original_data.get('fee', 0),
                            'original_fee_rate': tracked_tx.rbf_info.get('fee_analysis', {}).get('fee_rate_sat_vb', 0),
                            'age_seconds': tracked_tx.age_seconds(),
                            'timestamp': time.time(),
                            'new_txid': None  # We don't know the replacement txid yet
                        }
                        
                        replacements.append(replacement_info)
                        self.replacement_count += 1
                        
                        # Schedule for removal
                        to_remove.append(txid)
                
            except Exception as e:
                self.logger.error(f"Error checking replacement for {txid}: {e}")
        
        # Remove transactions that were replaced or confirmed
        for txid in to_remove:
            self.remove_transaction(txid, "replaced or confirmed")
        
        return replacements
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """Get statistics about tracked transactions"""
        if not self.tracked_transactions:
            return {
                'total_tracked': 0,
                'average_age': 0,
                'oldest_transaction': None,
                'total_replacements': self.replacement_count
            }
        
        ages = [tx.age_seconds() for tx in self.tracked_transactions.values()]
        oldest_tx = max(self.tracked_transactions.values(), key=lambda x: x.age_seconds())
        
        return {
            'total_tracked': len(self.tracked_transactions),
            'average_age': sum(ages) / len(ages),
            'oldest_transaction': {
                'txid': oldest_tx.txid,
                'age_seconds': oldest_tx.age_seconds()
            },
            'total_replacements': self.replacement_count
        }
