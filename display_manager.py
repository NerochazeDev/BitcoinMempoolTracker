"""
Display Manager - Handle terminal output and formatting
"""

import os
import sys
import time
import logging
from typing import Dict, Any
from datetime import datetime

class DisplayManager:
    """Manage terminal display for the RBF monitor"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 1  # Update display every second
        
        # Display counters
        self.total_rbf_detected = 0
        self.total_replacements = 0
        
        # Terminal settings
        self.terminal_width = self.get_terminal_width()
    
    def get_terminal_width(self) -> int:
        """Get terminal width, default to 80 if unable to determine"""
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_separator(self, char='-'):
        """Print a separator line"""
        print(char * self.terminal_width)
    
    def print_header(self, title: str):
        """Print a formatted header"""
        self.print_separator('=')
        print(f" {title} ".center(self.terminal_width))
        self.print_separator('=')
    
    def show_startup_banner(self):
        """Display startup banner"""
        self.clear_screen()
        self.print_header("Bitcoin Mempool RBF Monitor")
        print()
        print("Monitoring Bitcoin mempool for RBF (Replace-By-Fee) transactions...")
        print("Press Ctrl+C to stop")
        print()
        print("Status: Starting up...")
        self.print_separator()
        print()
    
    def format_time(self, timestamp: float) -> str:
        """Format timestamp for display"""
        return datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
    
    def format_fee_rate(self, fee_rate: float) -> str:
        """Format fee rate for display"""
        return f"{fee_rate:.2f} sat/vB"
    
    def format_btc_amount(self, satoshis: int) -> str:
        """Format satoshi amount as BTC"""
        return f"{satoshis / 100000000:.8f} BTC"
    
    def show_rbf_transaction(self, txid: str, tx_data: Dict, rbf_info: Dict):
        """Display a newly detected RBF transaction"""
        self.total_rbf_detected += 1
        
        print(f"\n🔄 RBF TRANSACTION DETECTED #{self.total_rbf_detected}")
        print(f"Time: {self.format_time(time.time())}")
        print(f"TxID: {txid}")
        
        # Basic transaction info
        fee_analysis = rbf_info.get('fee_analysis', {})
        tx_summary = rbf_info.get('transaction_summary', {})
        
        print(f"Fee: {fee_analysis.get('fee', 0)} sat ({self.format_fee_rate(fee_analysis.get('fee_rate_sat_vb', 0))})")
        print(f"Size: {fee_analysis.get('vsize', 0)} vB")
        print(f"Inputs: {tx_summary.get('input_count', 0)}")
        print(f"Outputs: {tx_summary.get('output_count', 0)}")
        
        # RBF specific info
        rbf_inputs = rbf_info.get('rbf_inputs', [])
        print(f"RBF Signaling: {len(rbf_inputs)}/{rbf_info.get('total_inputs', 0)} inputs signal RBF")
        
        for rbf_input in rbf_inputs[:3]:  # Show first 3 RBF inputs
            seq = rbf_input.get('sequence', 0)
            print(f"  Input {rbf_input.get('input_index', 0)}: sequence={seq} (0x{seq:08x})")
        
        if len(rbf_inputs) > 3:
            print(f"  ... and {len(rbf_inputs) - 3} more RBF inputs")
        
        self.print_separator()
    
    def show_rbf_replacement(self, replacement_info: Dict):
        """Display an RBF replacement event"""
        self.total_replacements += 1
        
        print(f"\n⚡ RBF REPLACEMENT DETECTED #{self.total_replacements}")
        print(f"Time: {self.format_time(replacement_info.get('timestamp', time.time()))}")
        print(f"Original TxID: {replacement_info.get('original_txid', 'unknown')}")
        
        if replacement_info.get('new_txid'):
            print(f"Replacement TxID: {replacement_info.get('new_txid')}")
        else:
            print("Replacement TxID: Unknown (transaction disappeared from mempool)")
        
        print(f"Original Fee Rate: {self.format_fee_rate(replacement_info.get('original_fee_rate', 0))}")
        print(f"Age when replaced: {replacement_info.get('age_seconds', 0):.1f} seconds")
        
        self.print_separator()
    
    def update_stats(self, total_mempool: int, tracked_rbf: int, total_replacements: int):
        """Update display with current statistics"""
        current_time = time.time()
        
        # Only update display periodically to avoid flickering
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Save cursor position and move to top
        print("\033[s", end="")  # Save cursor position
        print("\033[H", end="")  # Move to top
        
        # Update status line
        uptime = current_time - self.start_time
        uptime_str = f"{int(uptime // 3600):02d}:{int((uptime % 3600) // 60):02d}:{int(uptime % 60):02d}"
        
        status_line = (f"Status: Running | Uptime: {uptime_str} | "
                      f"Mempool: {total_mempool} txs | "
                      f"Tracking: {tracked_rbf} RBF | "
                      f"Detected: {self.total_rbf_detected} | "
                      f"Replacements: {total_replacements}")
        
        # Clear status line and print new one
        print(f"\033[K{status_line}")
        
        # Restore cursor position
        print("\033[u", end="")  # Restore cursor position
        sys.stdout.flush()
    
    def show_error(self, error_message: str):
        """Display an error message"""
        print(f"\n❌ ERROR: {error_message}")
        print(f"Time: {self.format_time(time.time())}")
        self.print_separator()
    
    def show_warning(self, warning_message: str):
        """Display a warning message"""
        print(f"\n⚠️  WARNING: {warning_message}")
        print(f"Time: {self.format_time(time.time())}")
        self.print_separator()
    
    def show_info(self, info_message: str):
        """Display an info message"""
        print(f"\nℹ️  INFO: {info_message}")
        print(f"Time: {self.format_time(time.time())}")
        self.print_separator()
