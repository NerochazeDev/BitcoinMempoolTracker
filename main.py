#!/usr/bin/env python3
"""
Bitcoin Mempool RBF Monitor - Main Entry Point
Real-time monitoring of Bitcoin mempool for RBF transactions
"""

import sys
import signal
import time
import logging
from mempool_monitor import MempoolMonitor
from display_manager import DisplayManager

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n[INFO] Shutting down mempool monitor...")
    sys.exit(0)

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('rbf_monitor.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main function to start the RBF monitoring"""
    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize display manager
    display = DisplayManager()
    
    # Initialize mempool monitor
    monitor = MempoolMonitor(display)
    
    logger.info("Starting Bitcoin Mempool RBF Monitor")
    display.show_startup_banner()
    
    try:
        # Start monitoring
        monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        display.show_error(f"Fatal error: {e}")
    finally:
        logger.info("Mempool monitor shutdown complete")

if __name__ == "__main__":
    main()
