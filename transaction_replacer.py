"""
Transaction Replacer - Create replacement transactions with higher fees
"""

import json
import hashlib
import struct
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, getcontext

# Set high precision for Bitcoin calculations
getcontext().prec = 50

class TransactionReplacer:
    """Create and manage Bitcoin transaction replacements"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_replacement_potential(self, tx_data: Dict) -> Dict[str, Any]:
        """
        Analyze if a transaction can be replaced and suggest improvements
        """
        try:
            # Check if transaction signals RBF
            can_replace = self._check_rbf_signaling(tx_data)
            if not can_replace:
                return {
                    'can_replace': False,
                    'reason': 'Transaction does not signal RBF (all inputs have sequence >= 0xfffffffe)'
                }
            
            # Calculate current fee rate
            current_fee = tx_data.get('fee', 0)
            vsize = tx_data.get('vsize', tx_data.get('size', 0))
            current_fee_rate = current_fee / vsize if vsize > 0 else 0
            
            # Suggest fee improvements
            suggested_rates = self._suggest_fee_rates(current_fee_rate)
            
            # Calculate output values
            outputs = tx_data.get('vout', [])
            total_output_value = sum(output.get('value', 0) for output in outputs)
            
            # Find change output (typically the largest output or one with specific patterns)
            change_output = self._identify_change_output(outputs)
            
            return {
                'can_replace': True,
                'current_fee': current_fee,
                'current_fee_rate': current_fee_rate,
                'vsize': vsize,
                'total_output_value': total_output_value,
                'change_output_index': change_output['index'] if change_output else None,
                'change_output_value': change_output['value'] if change_output else None,
                'suggested_fee_rates': suggested_rates,
                'replacement_strategies': self._generate_replacement_strategies(tx_data, suggested_rates)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing replacement potential: {e}")
            return {
                'can_replace': False,
                'reason': f'Analysis error: {str(e)}'
            }
    
    def _check_rbf_signaling(self, tx_data: Dict) -> bool:
        """Check if transaction signals RBF capability"""
        inputs = tx_data.get('vin', [])
        for inp in inputs:
            sequence = inp.get('sequence', 0xffffffff)
            if sequence < 0xfffffffe:
                return True
        return False
    
    def _suggest_fee_rates(self, current_rate: float) -> Dict[str, float]:
        """Suggest improved fee rates based on current rate"""
        return {
            'conservative': max(current_rate * 2.0, current_rate + 10, 15.0),
            'moderate': max(current_rate * 3.0, current_rate + 20, 25.0),
            'aggressive': max(current_rate * 5.0, current_rate + 50, 50.0),
            'priority': max(current_rate * 10.0, current_rate + 100, 100.0)
        }
    
    def _identify_change_output(self, outputs: List[Dict]) -> Optional[Dict]:
        """Identify the most likely change output"""
        if not outputs:
            return None
        
        # Simple heuristic: assume the largest output is change
        # In practice, this would need more sophisticated detection
        max_output = max(outputs, key=lambda x: x.get('value', 0))
        max_index = outputs.index(max_output)
        
        return {
            'index': max_index,
            'value': max_output.get('value', 0),
            'script': max_output.get('scriptpubkey', '')
        }
    
    def _generate_replacement_strategies(self, tx_data: Dict, suggested_rates: Dict[str, float]) -> List[Dict]:
        """Generate different replacement strategies"""
        strategies = []
        current_fee = tx_data.get('fee', 0)
        vsize = tx_data.get('vsize', tx_data.get('size', 0))
        
        for strategy_name, new_rate in suggested_rates.items():
            new_fee = int(new_rate * vsize)
            fee_increase = new_fee - current_fee
            
            strategies.append({
                'name': strategy_name,
                'new_fee_rate': new_rate,
                'new_total_fee': new_fee,
                'fee_increase': fee_increase,
                'description': f'{strategy_name.title()} replacement: {new_rate:.2f} sat/vB'
            })
        
        return strategies
    
    def create_replacement_transaction(self, original_tx: Dict, strategy: str = 'moderate') -> Dict[str, Any]:
        """
        Create a replacement transaction with higher fee
        
        Note: This creates the transaction structure but does not sign it.
        Actual signing requires private keys which should be handled securely.
        """
        try:
            analysis = self.analyze_replacement_potential(original_tx)
            
            if not analysis['can_replace']:
                return {
                    'success': False,
                    'error': analysis['reason']
                }
            
            # Find the selected strategy
            selected_strategy = None
            for strat in analysis['replacement_strategies']:
                if strat['name'] == strategy:
                    selected_strategy = strat
                    break
            
            if not selected_strategy:
                return {
                    'success': False,
                    'error': f'Strategy "{strategy}" not found'
                }
            
            # Create new transaction structure
            new_tx = self._build_replacement_transaction(original_tx, selected_strategy, analysis)
            
            return {
                'success': True,
                'original_txid': original_tx.get('txid'),
                'replacement_transaction': new_tx,
                'strategy_used': selected_strategy,
                'fee_increase': selected_strategy['fee_increase'],
                'new_fee_rate': selected_strategy['new_fee_rate'],
                'signing_required': True,
                'warning': 'Transaction created but requires signing with private keys'
            }
            
        except Exception as e:
            self.logger.error(f"Error creating replacement transaction: {e}")
            return {
                'success': False,
                'error': f'Creation error: {str(e)}'
            }
    
    def _build_replacement_transaction(self, original_tx: Dict, strategy: Dict, analysis: Dict) -> Dict:
        """Build the replacement transaction structure"""
        # Copy original transaction structure
        new_tx = {
            'version': original_tx.get('version', 1),
            'locktime': original_tx.get('locktime', 0),
            'vin': [],
            'vout': []
        }
        
        # Copy all inputs (same UTXOs, but we'll update sequences to ensure RBF)
        for inp in original_tx.get('vin', []):
            new_input = inp.copy()
            # Ensure RBF signaling (sequence < 0xfffffffe)
            new_input['sequence'] = min(inp.get('sequence', 0xffffffff), 0xfffffffd)
            new_tx['vin'].append(new_input)
        
        # Handle outputs - reduce change output to increase fee
        original_outputs = original_tx.get('vout', [])
        change_index = analysis.get('change_output_index')
        fee_increase = strategy['fee_increase']
        
        for i, output in enumerate(original_outputs):
            new_output = output.copy()
            
            # If this is the change output, reduce it by the fee increase
            if i == change_index and change_index is not None:
                original_value = output.get('value', 0)
                new_value = max(0, original_value - fee_increase)
                
                # Only include output if it has meaningful value (> 546 sat dust limit)
                if new_value > 546:
                    new_output['value'] = new_value
                    new_tx['vout'].append(new_output)
                # If change becomes dust, skip it (fee increases by the full change amount)
            else:
                # Keep other outputs unchanged
                new_tx['vout'].append(new_output)
        
        return new_tx
    
    def estimate_replacement_priority(self, current_fee_rate: float) -> Dict[str, Any]:
        """
        Estimate how urgent a replacement might be based on current network conditions
        """
        # These would ideally come from real-time fee estimation APIs
        network_fee_levels = {
            'low_priority': 1.0,
            'medium_priority': 5.0,
            'high_priority': 10.0,
            'urgent': 20.0
        }
        
        priority_level = 'low'
        if current_fee_rate < network_fee_levels['low_priority']:
            priority_level = 'urgent'
        elif current_fee_rate < network_fee_levels['medium_priority']:
            priority_level = 'high'
        elif current_fee_rate < network_fee_levels['high_priority']:
            priority_level = 'medium'
        
        return {
            'current_fee_rate': current_fee_rate,
            'priority_level': priority_level,
            'network_fee_levels': network_fee_levels,
            'recommendation': self._get_priority_recommendation(priority_level)
        }
    
    def _get_priority_recommendation(self, priority_level: str) -> str:
        """Get recommendation based on priority level"""
        recommendations = {
            'low': 'Transaction fee is competitive. Replacement optional.',
            'medium': 'Consider moderate fee increase for faster confirmation.',
            'high': 'Recommend fee increase to avoid delays.',
            'urgent': 'Immediate replacement recommended - very low fee rate.'
        }
        return recommendations.get(priority_level, 'Unable to assess priority.')
    
    def validate_replacement_transaction(self, replacement_tx: Dict, original_tx: Dict) -> Dict[str, Any]:
        """
        Validate that a replacement transaction follows RBF rules
        """
        try:
            # Check 1: Same inputs (BIP 125 requirement)
            original_inputs = set()
            replacement_inputs = set()
            
            for inp in original_tx.get('vin', []):
                utxo = f"{inp.get('txid', '')}:{inp.get('vout', 0)}"
                original_inputs.add(utxo)
            
            for inp in replacement_tx.get('vin', []):
                utxo = f"{inp.get('txid', '')}:{inp.get('vout', 0)}"
                replacement_inputs.add(utxo)
            
            if original_inputs != replacement_inputs:
                return {
                    'valid': False,
                    'error': 'Replacement transaction must spend the same UTXOs'
                }
            
            # Check 2: Higher fee
            original_fee = original_tx.get('fee', 0)
            replacement_fee = replacement_tx.get('fee', 0)
            
            if replacement_fee <= original_fee:
                return {
                    'valid': False,
                    'error': 'Replacement transaction must have higher fee'
                }
            
            # Check 3: RBF signaling
            rbf_signaled = False
            for inp in replacement_tx.get('vin', []):
                if inp.get('sequence', 0xffffffff) < 0xfffffffe:
                    rbf_signaled = True
                    break
            
            if not rbf_signaled:
                return {
                    'valid': False,
                    'error': 'Replacement transaction must signal RBF'
                }
            
            return {
                'valid': True,
                'fee_increase': replacement_fee - original_fee,
                'original_fee': original_fee,
                'replacement_fee': replacement_fee
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }