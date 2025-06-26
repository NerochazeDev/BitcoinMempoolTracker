#!/usr/bin/env python3
"""
High-Value Transaction Monitor - Start monitoring for $1k+ RBF transactions
"""

from auto_replacer import AutoReplacer
import sys

def start_monitoring():
    """Start monitoring for high-value RBF transactions"""
    
    target_address = "1JHPrMhXRkd5LszkpPog7wVtpGfNHur2M9"
    strategy = "aggressive"  # Higher fees for faster confirmation
    min_value = 1000.0      # Only target $1k+ transactions
    duration = 60           # Run for 1 hour
    
    print(f"Starting High-Value RBF Monitor")
    print(f"Target: {target_address}")
    print(f"Minimum value: ${min_value:.0f}")
    print(f"Strategy: {strategy}")
    print("="*60)
    
    replacer = AutoReplacer(target_address, strategy, min_value)
    try:
        replacer.monitor_and_replace(duration)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        print(f"Final stats: {replacer.replacement_count} replacements, {replacer.skipped_count} skipped")

if __name__ == "__main__":
    start_monitoring()