#!/usr/bin/env python3
"""
RBF Replacement Demo - Simple demonstration of transaction replacement
"""

import sys
import json
from rbf_cli import RBFCommandLine

def demo_replacement():
    """Demonstrate transaction replacement functionality"""
    print("🔄 Bitcoin RBF Transaction Replacement Demo")
    print("=" * 60)
    print()
    
    # Initialize the CLI
    cli = RBFCommandLine()
    
    print("This tool can help you replace Bitcoin transactions with higher fees.")
    print("You'll need a transaction ID (txid) that signals RBF capability.")
    print()
    
    # Get transaction ID from user
    while True:
        txid = input("Enter transaction ID to analyze (or 'quit' to exit): ").strip()
        
        if txid.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            return
        
        if len(txid) != 64:
            print("❌ Transaction ID must be 64 characters long")
            continue
            
        break
    
    print()
    print("🔍 Analyzing transaction...")
    
    # Analyze the transaction
    tx_data = cli.fetch_transaction(txid)
    if not tx_data:
        print("❌ Could not fetch transaction. Please check the transaction ID.")
        return
    
    analysis = cli.replacer.analyze_replacement_potential(tx_data)
    
    if not analysis['can_replace']:
        print(f"❌ Cannot replace transaction: {analysis['reason']}")
        return
    
    print("✅ Transaction can be replaced!")
    print()
    
    # Show current transaction details
    print("📊 CURRENT TRANSACTION:")
    print(f"  Fee: {analysis['current_fee']} sat")
    print(f"  Fee Rate: {analysis['current_fee_rate']:.2f} sat/vB")
    print(f"  Size: {analysis['vsize']} vB")
    
    # Show replacement options
    print()
    print("💡 REPLACEMENT OPTIONS:")
    strategies = analysis['replacement_strategies']
    for i, strategy in enumerate(strategies, 1):
        print(f"  {i}. {strategy['name'].upper()}: {strategy['new_fee_rate']:.2f} sat/vB "
              f"(+{strategy['fee_increase']} sat)")
    
    # Get user choice
    print()
    while True:
        try:
            choice = input("Select replacement strategy (1-4) or 'skip': ").strip()
            
            if choice.lower() in ['skip', 's']:
                print("Skipping replacement creation.")
                return
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(strategies):
                selected_strategy = strategies[choice_num - 1]['name']
                break
            else:
                print("❌ Please enter a number between 1 and 4")
        except ValueError:
            print("❌ Please enter a valid number")
    
    print()
    print(f"🔧 Creating replacement with {selected_strategy} strategy...")
    
    # Create replacement
    result = cli.replacer.create_replacement_transaction(tx_data, selected_strategy)
    
    if not result['success']:
        print(f"❌ Failed to create replacement: {result['error']}")
        return
    
    print("✅ Replacement transaction created!")
    print()
    
    # Show replacement details
    print("📋 REPLACEMENT SUMMARY:")
    print(f"  Original TxID: {result['original_txid']}")
    print(f"  Strategy: {result['strategy_used']['name']}")
    print(f"  New Fee Rate: {result['new_fee_rate']:.2f} sat/vB")
    print(f"  Fee Increase: +{result['fee_increase']} sat")
    
    # Save result
    filename = f"replacement_{txid[:16]}.json"
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"💾 Full replacement data saved to: {filename}")
    print()
    print("⚠️  IMPORTANT NOTES:")
    print("  • This transaction is NOT signed and cannot be broadcast")
    print("  • You need your private keys to sign the transaction")
    print("  • Never share private keys with anyone")
    print("  • Use proper wallet software to sign transactions")
    print()
    
    # Ask if user wants to see raw transaction
    show_raw = input("Show raw transaction structure? (y/n): ").strip().lower()
    if show_raw in ['y', 'yes']:
        print()
        print("🔧 RAW TRANSACTION STRUCTURE:")
        replacement_tx = result['replacement_transaction']
        print(json.dumps(replacement_tx, indent=2))

def main():
    """Main entry point"""
    try:
        demo_replacement()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()