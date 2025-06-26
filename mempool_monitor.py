"""
Mempool Monitor - Core monitoring functionality
"""

import time
import json
import logging
import requests
from typing import Dict, Set, Optional
from rbf_detector import RBFDetector
from transaction_tracker import TransactionTracker
from display_manager import DisplayManager
from config import Config

class MempoolMonitor:
    """Main class for monitoring Bitcoin mempool"""
    
    def __init__(self, display_manager: DisplayManager):
        self.logger = logging.getLogger(__name__)
        self.display = display_manager
        self.rbf_detector = RBFDetector()
        self.tracker = TransactionTracker()
        self.config = Config()
        
        # Track seen transactions to detect new ones
        self.seen_txids: Set[str] = set()
        
        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Bitcoin-RBF-Monitor/1.0'
        })
    
    def get_mempool_txids(self) -> Optional[Set[str]]:
        """Fetch current mempool transaction IDs"""
        try:
            response = self.session.get(
                f"{self.config.MEMPOOL_API_BASE}/mempool/txids",
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            txids = set(response.json())
            self.logger.debug(f"Fetched {len(txids)} mempool transactions")
            return txids
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch mempool txids: {e}")
            self.display.show_error(f"API Error: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse mempool response: {e}")
            return None
    
    def get_transaction_details(self, txid: str) -> Optional[Dict]:
        """Fetch detailed transaction information"""
        try:
            response = self.session.get(
                f"{self.config.MEMPOOL_API_BASE}/tx/{txid}",
                timeout=self.config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            tx_data = response.json()
            self.logger.debug(f"Fetched details for transaction {txid}")
            return tx_data
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch transaction {txid}: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse transaction response: {e}")
            return None
    
    def process_new_transactions(self, new_txids: Set[str]) -> None:
        """Process newly discovered transactions"""
        for txid in new_txids:
            try:
                # Get transaction details
                tx_data = self.get_transaction_details(txid)
                if not tx_data:
                    continue
                
                # Check if transaction signals RBF
                rbf_info = self.rbf_detector.analyze_transaction(tx_data)
                
                if rbf_info['is_rbf']:
                    self.logger.info(f"RBF transaction detected: {txid}")
                    
                    # Track the transaction
                    self.tracker.add_transaction(txid, tx_data, rbf_info)
                    
                    # Display the transaction
                    self.display.show_rbf_transaction(txid, tx_data, rbf_info)
                
                # Small delay to avoid overwhelming the API
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error processing transaction {txid}: {e}")
    
    def check_for_replacements(self) -> None:
        """Check tracked transactions for replacements"""
        replacements = self.tracker.check_for_replacements(self.get_transaction_details)
        
        for replacement_info in replacements:
            self.logger.info(f"RBF replacement detected: {replacement_info['original_txid']} -> {replacement_info['new_txid']}")
            self.display.show_rbf_replacement(replacement_info)
    
    def monitoring_cycle(self) -> bool:
        """Single monitoring cycle - returns True if successful"""
        try:
            # Get current mempool
            current_txids = self.get_mempool_txids()
            if current_txids is None:
                return False
            
            # Find new transactions
            new_txids = current_txids - self.seen_txids
            
            if new_txids:
                self.logger.info(f"Processing {len(new_txids)} new transactions")
                self.process_new_transactions(new_txids)
            
            # Update seen transactions (keep only those still in mempool)
            self.seen_txids = current_txids
            
            # Check for replacements of tracked transactions
            self.check_for_replacements()
            
            # Update display stats
            self.display.update_stats(
                total_mempool=len(current_txids),
                tracked_rbf=len(self.tracker.tracked_transactions),
                total_replacements=self.tracker.replacement_count
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            self.display.show_error(f"Monitoring error: {e}")
            return False
    
    def start_monitoring(self) -> None:
        """Start the main monitoring loop"""
        consecutive_failures = 0
        max_failures = self.config.MAX_CONSECUTIVE_FAILURES
        
        while True:
            success = self.monitoring_cycle()
            
            if success:
                consecutive_failures = 0
                time.sleep(self.config.MONITORING_INTERVAL)
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    error_msg = f"Too many consecutive failures ({consecutive_failures}). Stopping monitor."
                    self.logger.error(error_msg)
                    self.display.show_error(error_msg)
                    break
                
                # Exponential backoff on failures
                backoff_time = min(60, 2 ** consecutive_failures)
                self.logger.warning(f"Backing off for {backoff_time} seconds after failure {consecutive_failures}")
                time.sleep(backoff_time)
