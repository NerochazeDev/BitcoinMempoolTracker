"""
RBF Command Line Interface - Interactive tool for transaction replacement
"""

import sys
import json
import requests
import argparse
from typing import Dict, Optional, Any
from transaction_replacer import TransactionReplacer
from config import Config
from display_manager import DisplayManager

class RBFCommandLine:
    """Command line interface for RBF operations"""
    
    def __init__(self):
        self.replacer = TransactionReplacer()
        self.display = DisplayManager()
        self.config = Config()
        
    def fetch_transaction(self, txid: str) -> Optional[Dict]:
        """Fetch transaction data from API"""
        try:
            url = f"{self.config.get_api_url()}/tx/{txid}"
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching transaction: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching transaction: {e}")
            return None
    
    def analyze_transaction(self, txid: str) -> None:
        """Analyze a transaction for replacement potential"""
        print(f"Analyzing transaction: {txid}")
        print("=" * 60)
        
        # Fetch transaction data
        tx_data = self.fetch_transaction(txid)
        if not tx_data:
            print("❌ Could not fetch transaction data")
            return
        
        # Analyze replacement potential
        analysis = self.replacer.analyze_replacement_potential(tx_data)
        
        if not analysis['can_replace']:
            print(f"❌ Cannot replace transaction: {analysis['reason']}")
            return
        
        # Display analysis results
        print("✅ Transaction can be replaced (RBF enabled)")
        print()
        
        print("📊 CURRENT TRANSACTION:")
        print(f"  Fee: {analysis['current_fee']} sat")
        print(f"  Fee Rate: {analysis['current_fee_rate']:.2f} sat/vB")
        print(f"  Size: {analysis['vsize']} vB")
        print(f"  Total Output Value: {analysis['total_output_value']} sat")
        
        if analysis.get('change_output_index') is not None:
            print(f"  Change Output: #{analysis['change_output_index']} ({analysis['change_output_value']} sat)")
        
        print()
        print("💡 REPLACEMENT STRATEGIES:")
        for strategy in analysis['replacement_strategies']:
            print(f"  {strategy['name'].upper()}: {strategy['new_fee_rate']:.2f} sat/vB "
                  f"(+{strategy['fee_increase']} sat fee)")
        
        # Show priority assessment
        priority = self.replacer.estimate_replacement_priority(analysis['current_fee_rate'])
        print()
        print("⚡ PRIORITY ASSESSMENT:")
        print(f"  Current Priority: {priority['priority_level'].upper()}")
        print(f"  Recommendation: {priority['recommendation']}")
    
    def create_replacement(self, txid: str, strategy: str = 'moderate') -> None:
        """Create a replacement transaction"""
        print(f"Creating replacement transaction for: {txid}")
        print(f"Strategy: {strategy}")
        print("=" * 60)
        
        # Fetch transaction data
        tx_data = self.fetch_transaction(txid)
        if not tx_data:
            print("❌ Could not fetch transaction data")
            return
        
        # Create replacement
        result = self.replacer.create_replacement_transaction(tx_data, strategy)
        
        if not result['success']:
            print(f"❌ Failed to create replacement: {result['error']}")
            return
        
        print("✅ Replacement transaction created successfully")
        print()
        
        # Display replacement details
        print("📋 REPLACEMENT DETAILS:")
        print(f"  Original TxID: {result['original_txid']}")
        print(f"  Strategy Used: {result['strategy_used']['name']}")
        print(f"  New Fee Rate: {result['new_fee_rate']:.2f} sat/vB")
        print(f"  Fee Increase: +{result['fee_increase']} sat")
        
        print()
        print("🔧 TRANSACTION STRUCTURE:")
        replacement_tx = result['replacement_transaction']
        print(f"  Version: {replacement_tx['version']}")
        print(f"  Inputs: {len(replacement_tx['vin'])}")
        print(f"  Outputs: {len(replacement_tx['vout'])}")
        print(f"  Locktime: {replacement_tx['locktime']}")
        
        # Show inputs
        print()
        print("📥 INPUTS:")
        for i, inp in enumerate(replacement_tx['vin']):
            print(f"  #{i}: {inp.get('txid', 'N/A')}:{inp.get('vout', 'N/A')} "
                  f"(seq: {inp.get('sequence', 'N/A')})")
        
        # Show outputs
        print()
        print("📤 OUTPUTS:")
        for i, out in enumerate(replacement_tx['vout']):
            print(f"  #{i}: {out.get('value', 0)} sat")
        
        print()
        print("⚠️  WARNING: This transaction requires signing with private keys")
        print("⚠️  Do not share private keys or sign untrusted transactions")
        
        # Save to file
        output_file = f"replacement_{txid[:16]}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"💾 Full replacement data saved to: {output_file}")
    
    def validate_replacement(self, original_txid: str, replacement_file: str) -> None:
        """Validate a replacement transaction"""
        print(f"Validating replacement transaction")
        print("=" * 60)
        
        # Load replacement transaction
        try:
            with open(replacement_file, 'r') as f:
                replacement_data = json.load(f)
        except Exception as e:
            print(f"❌ Error loading replacement file: {e}")
            return
        
        # Fetch original transaction
        original_tx = self.fetch_transaction(original_txid)
        if not original_tx:
            print("❌ Could not fetch original transaction")
            return
        
        # Validate
        replacement_tx = replacement_data.get('replacement_transaction', {})
        validation = self.replacer.validate_replacement_transaction(replacement_tx, original_tx)
        
        if validation['valid']:
            print("✅ Replacement transaction is valid")
            print(f"  Original Fee: {validation['original_fee']} sat")
            print(f"  Replacement Fee: {validation['replacement_fee']} sat")
            print(f"  Fee Increase: +{validation['fee_increase']} sat")
        else:
            print(f"❌ Replacement transaction is invalid: {validation['error']}")
    
    def interactive_mode(self) -> None:
        """Interactive mode for RBF operations"""
        print("🔄 Bitcoin RBF Transaction Replacer")
        print("=" * 60)
        print("Interactive mode - Enter commands or 'help' for assistance")
        print()
        
        while True:
            try:
                command = input("rbf> ").strip().lower()
                
                if command in ['exit', 'quit', 'q']:
                    print("Goodbye!")
                    break
                elif command in ['help', 'h']:
                    self.show_help()
                elif command.startswith('analyze '):
                    txid = command.replace('analyze ', '').strip()
                    if len(txid) == 64:  # Bitcoin txid length
                        self.analyze_transaction(txid)
                    else:
                        print("❌ Invalid transaction ID length")
                elif command.startswith('replace '):
                    parts = command.replace('replace ', '').strip().split()
                    if len(parts) >= 1:
                        txid = parts[0]
                        strategy = parts[1] if len(parts) > 1 else 'moderate'
                        if len(txid) == 64:
                            self.create_replacement(txid, strategy)
                        else:
                            print("❌ Invalid transaction ID length")
                    else:
                        print("❌ Usage: replace <txid> [strategy]")
                elif command == '':
                    continue
                else:
                    print("❌ Unknown command. Type 'help' for assistance.")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def show_help(self) -> None:
        """Show help information"""
        print()
        print("📚 AVAILABLE COMMANDS:")
        print("  analyze <txid>           - Analyze transaction for RBF potential")
        print("  replace <txid> [strategy] - Create replacement transaction")
        print("  help                     - Show this help")
        print("  exit                     - Exit program")
        print()
        print("📊 REPLACEMENT STRATEGIES:")
        print("  conservative - 25% fee increase (minimum +1 sat/vB)")
        print("  moderate     - 50% fee increase (minimum +5 sat/vB)")
        print("  aggressive   - 100% fee increase (minimum +10 sat/vB)")
        print("  priority     - 200% fee increase (minimum +20 sat/vB)")
        print()
        print("💡 EXAMPLES:")
        print("  analyze 1a2b3c4d5e6f...")
        print("  replace 1a2b3c4d5e6f... aggressive")
        print()

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Bitcoin RBF Transaction Replacer")
    parser.add_argument('command', nargs='?', choices=['analyze', 'replace', 'validate', 'interactive'],
                       help='Command to execute')
    parser.add_argument('txid', nargs='?', help='Transaction ID')
    parser.add_argument('--strategy', default='moderate', 
                       choices=['conservative', 'moderate', 'aggressive', 'priority'],
                       help='Replacement strategy')
    parser.add_argument('--file', help='Replacement transaction file for validation')
    
    args = parser.parse_args()
    cli = RBFCommandLine()
    
    if args.command == 'analyze' and args.txid:
        cli.analyze_transaction(args.txid)
    elif args.command == 'replace' and args.txid:
        cli.create_replacement(args.txid, args.strategy)
    elif args.command == 'validate' and args.txid and args.file:
        cli.validate_replacement(args.txid, args.file)
    elif args.command == 'interactive' or not args.command:
        cli.interactive_mode()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()