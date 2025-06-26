# Bitcoin RBF Monitor & Transaction Replacer

A comprehensive Bitcoin mempool monitoring system that detects Replace-By-Fee (RBF) transactions and provides tools to create replacement transactions with higher fees.

## Features

### Monitoring
- Real-time Bitcoin mempool monitoring
- Automatic RBF transaction detection using BIP 125 signaling
- Transaction tracking and replacement detection
- Live statistics and display updates

### Transaction Replacement
- Analyze transactions for replacement potential
- Create replacement transactions with higher fees
- Multiple fee increase strategies
- BIP 125 compliance validation
- Interactive command-line interface

## Quick Start

### 1. Run the Monitor
```bash
python main.py
```

This starts the real-time mempool monitor that displays RBF transactions as they appear.

### 2. Use Transaction Replacement

#### Interactive Demo
```bash
python replace_demo.py
```

#### Command Line Interface
```bash
python rbf_cli.py interactive
```

#### Direct Commands
```bash
# Analyze a transaction
python rbf_cli.py analyze <transaction_id>

# Create replacement transaction
python rbf_cli.py replace <transaction_id> --strategy moderate
```

## Transaction Replacement Guide

### How It Works

1. **Detection**: The system identifies transactions that signal RBF capability
2. **Analysis**: Evaluates replacement potential and suggests fee strategies
3. **Creation**: Builds new transaction structure with higher fees
4. **Validation**: Ensures compliance with BIP 125 replacement rules

### Fee Strategies

- **Conservative**: 25% fee increase (minimum +1 sat/vB)
- **Moderate**: 50% fee increase (minimum +5 sat/vB)
- **Aggressive**: 100% fee increase (minimum +10 sat/vB)
- **Priority**: 200% fee increase (minimum +20 sat/vB)

### Example Usage

```python
from rbf_cli import RBFCommandLine

cli = RBFCommandLine()

# Analyze a transaction
txid = "1a2b3c4d5e6f7890abcdef..."
analysis = cli.analyze_transaction(txid)

# Create replacement
replacement = cli.create_replacement(txid, "moderate")
```

## Important Security Notes

### Transaction Signing
- Replacement transactions are created but **NOT signed**
- You need your private keys to sign transactions
- Never share private keys with anyone
- Use proper wallet software for signing

### Broadcasting
- Only broadcast transactions you have signed yourself
- Verify all transaction details before broadcasting
- Understand the fee implications of replacements

## Configuration

All settings can be configured via environment variables:

```bash
# API settings
MEMPOOL_API_BASE=https://mempool.space/api
REQUEST_TIMEOUT=30

# Monitoring intervals
MONITORING_INTERVAL=10
UPDATE_DISPLAY_INTERVAL=1

# Fee analysis
MIN_REQUEST_INTERVAL=0.1
```

## File Structure

```
├── main.py                 # Main monitor application
├── mempool_monitor.py      # Core monitoring logic
├── rbf_detector.py         # RBF signal detection
├── transaction_tracker.py  # Transaction lifecycle tracking
├── transaction_replacer.py # Replacement transaction creation
├── rbf_cli.py             # Command-line interface
├── replace_demo.py        # Interactive demonstration
├── display_manager.py     # Terminal output formatting
└── config.py              # Configuration management
```

## API Endpoints Used

- **Primary**: Mempool.space API (https://mempool.space/api)
- **Backup**: Blockstream.info API (https://blockstream.info/api)

## Requirements

- Python 3.11+
- requests library
- Internet connection for Bitcoin API access

## License

This project is provided as-is for educational and research purposes. Use responsibly and understand Bitcoin transaction mechanics before creating replacement transactions.

## Troubleshooting

### Common Issues

1. **Transaction not found**: Verify the transaction ID is correct and the transaction is still in the mempool
2. **Cannot replace**: Check if the transaction signals RBF (sequence numbers < 0xfffffffe)
3. **API errors**: The system automatically switches to backup APIs on failures

### Getting Help

Run the interactive mode for guided assistance:
```bash
python rbf_cli.py interactive
```

Or use the demo script for a step-by-step walkthrough:
```bash
python replace_demo.py
```