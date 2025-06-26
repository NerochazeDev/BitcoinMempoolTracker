# Bitcoin RBF Monitor

## Overview

This project is a real-time Bitcoin mempool monitoring system designed to detect and track Replace-By-Fee (RBF) transactions. It continuously monitors the Bitcoin mempool, identifies transactions that signal RBF capability, and tracks when these transactions are replaced by new versions with higher fees.

## System Architecture

The application follows a modular Python architecture with clear separation of concerns:

### Core Components
- **Monitor Core**: `MempoolMonitor` - Main orchestration and API communication
- **RBF Detection**: `RBFDetector` - Implements BIP 125 RBF signaling detection
- **Transaction Tracking**: `TransactionTracker` - Manages lifecycle of RBF transactions
- **Display Management**: `DisplayManager` - Handles terminal output and user interface
- **Configuration**: `Config` - Centralized configuration management

### Technology Stack
- **Runtime**: Python 3.11
- **HTTP Client**: requests library for API communication
- **APIs**: Mempool.space and Blockstream.info as backup
- **Deployment**: Replit environment with Nix package management

## Key Components

### MempoolMonitor
- Fetches current mempool transaction IDs from external APIs
- Coordinates between RBF detection and transaction tracking
- Implements error handling and API failover mechanisms
- Manages session persistence for efficient HTTP connections

### RBFDetector
- Implements BIP 125 RBF signaling detection
- Analyzes transaction input sequence numbers (< 0xfffffffe indicates RBF)
- Provides detailed reporting on which inputs signal RBF capability

### TransactionTracker
- Maintains state of tracked RBF transactions
- Detects when transactions are replaced by monitoring input UTXO conflicts
- Implements automatic cleanup of old transactions
- Tracks replacement statistics and transaction lifecycle

### DisplayManager
- Provides real-time terminal interface
- Shows monitoring statistics and RBF detection results
- Handles screen clearing and formatted output
- Implements responsive display updates

## Data Flow

1. **Mempool Polling**: Monitor fetches current mempool transaction IDs
2. **New Transaction Detection**: Identifies transactions not previously seen
3. **RBF Analysis**: Each new transaction is analyzed for RBF signaling
4. **Tracking Registration**: RBF-capable transactions are added to tracker
5. **Replacement Detection**: Ongoing monitoring for transaction replacements
6. **Display Updates**: Real-time terminal output of monitoring results
7. **Cleanup**: Automatic removal of old/confirmed transactions

## External Dependencies

### APIs
- **Primary**: Mempool.space API (`https://mempool.space/api`)
- **Backup**: Blockstream.info API (`https://blockstream.info/api`)

### Python Packages
- `requests>=2.32.4` - HTTP client for API communication
- Standard library modules for logging, configuration, and system utilities

## Deployment Strategy

The application is designed for Replit deployment with the following characteristics:

### Environment Setup
- Python 3.11 runtime via Nix package manager
- Automatic dependency installation via pip
- Single-command execution through Replit workflows

### Configuration
- Environment variable-based configuration system
- Sensible defaults for all settings
- Runtime configuration without code changes

### Monitoring Intervals
- 10-second mempool polling interval (configurable)
- 1-second display update frequency
- 5-minute cleanup cycle for old transactions

### Error Handling
- API failover to backup services
- Graceful degradation on network issues
- Automatic retry mechanisms with exponential backoff

## Changelog

```
Changelog:
- June 26, 2025. Initial setup
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```