"""
Configuration settings for the Bitcoin Mempool RBF Monitor
"""

import os

class Config:
    """Configuration class for the RBF monitor"""
    
    # API Configuration
    MEMPOOL_API_BASE = os.getenv('MEMPOOL_API_BASE', 'https://mempool.space/api')
    
    # Alternative APIs (in case primary fails)
    BACKUP_APIS = [
        'https://blockstream.info/api',
        'https://mempool.space/api'
    ]
    
    # Timing Configuration
    MONITORING_INTERVAL = float(os.getenv('MONITORING_INTERVAL', '10'))  # seconds between checks
    REQUEST_TIMEOUT = float(os.getenv('REQUEST_TIMEOUT', '30'))          # API request timeout
    
    # Error Handling
    MAX_CONSECUTIVE_FAILURES = int(os.getenv('MAX_CONSECUTIVE_FAILURES', '5'))
    
    # Transaction Tracking
    MAX_TRACKING_TIME = int(os.getenv('MAX_TRACKING_TIME', '3600'))      # 1 hour
    CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', '300'))         # 5 minutes
    
    # Display Configuration
    UPDATE_DISPLAY_INTERVAL = float(os.getenv('UPDATE_DISPLAY_INTERVAL', '1'))  # seconds
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'rbf_monitor.log')
    
    # Rate Limiting (to be respectful to APIs)
    MIN_REQUEST_INTERVAL = float(os.getenv('MIN_REQUEST_INTERVAL', '0.1'))  # minimum time between requests
    
    # Feature Flags
    ENABLE_DETAILED_LOGGING = os.getenv('ENABLE_DETAILED_LOGGING', 'false').lower() == 'true'
    ENABLE_RBF_ALERTS = os.getenv('ENABLE_RBF_ALERTS', 'true').lower() == 'true'
    
    @classmethod
    def get_api_url(cls) -> str:
        """Get the primary API URL"""
        return cls.MEMPOOL_API_BASE
    
    @classmethod
    def get_backup_apis(cls) -> list:
        """Get list of backup API URLs"""
        return cls.BACKUP_APIS.copy()
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings"""
        try:
            # Check if monitoring interval is reasonable
            if cls.MONITORING_INTERVAL < 1:
                print(f"Warning: MONITORING_INTERVAL ({cls.MONITORING_INTERVAL}) is very low, may overwhelm API")
                return False
            
            # Check if timeout is reasonable
            if cls.REQUEST_TIMEOUT < 5:
                print(f"Warning: REQUEST_TIMEOUT ({cls.REQUEST_TIMEOUT}) is very low")
                return False
            
            return True
            
        except Exception as e:
            print(f"Configuration validation error: {e}")
            return False
    
    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("=== Bitcoin RBF Monitor Configuration ===")
        print(f"API Base URL: {cls.MEMPOOL_API_BASE}")
        print(f"Monitoring Interval: {cls.MONITORING_INTERVAL} seconds")
        print(f"Request Timeout: {cls.REQUEST_TIMEOUT} seconds")
        print(f"Max Consecutive Failures: {cls.MAX_CONSECUTIVE_FAILURES}")
        print(f"Max Tracking Time: {cls.MAX_TRACKING_TIME} seconds")
        print(f"Detailed Logging: {cls.ENABLE_DETAILED_LOGGING}")
        print(f"RBF Alerts: {cls.ENABLE_RBF_ALERTS}")
        print("==========================================")
