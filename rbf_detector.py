"""
RBF Detector - Detect Replace-By-Fee signals in Bitcoin transactions
"""

import logging
from typing import Dict, List, Any

class RBFDetector:
    """Detect RBF (Replace-By-Fee) signals in Bitcoin transactions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_bip125_signaling(self, tx_data: Dict) -> Dict[str, Any]:
        """
        Check for BIP 125 RBF signaling
        A transaction signals RBF if any of its inputs has a sequence number < 0xfffffffe
        """
        rbf_inputs = []
        is_rbf = False
        
        try:
            # Check each input for RBF signaling
            for i, vin in enumerate(tx_data.get('vin', [])):
                sequence = vin.get('sequence', 0xffffffff)
                
                # BIP 125: sequence < 0xfffffffe signals RBF
                if sequence < 0xfffffffe:
                    is_rbf = True
                    rbf_inputs.append({
                        'input_index': i,
                        'sequence': sequence,
                        'txid': vin.get('txid', 'unknown'),
                        'vout': vin.get('vout', 0)
                    })
            
            return {
                'is_rbf': is_rbf,
                'signaling_method': 'BIP125' if is_rbf else None,
                'rbf_inputs': rbf_inputs,
                'total_inputs': len(tx_data.get('vin', [])),
                'rbf_input_count': len(rbf_inputs)
            }
            
        except Exception as e:
            self.logger.error(f"Error checking BIP125 signaling: {e}")
            return {
                'is_rbf': False,
                'error': str(e)
            }
    
    def analyze_transaction_fees(self, tx_data: Dict) -> Dict[str, Any]:
        """Analyze transaction fee structure for RBF potential"""
        try:
            fee = tx_data.get('fee', 0)
            size = tx_data.get('size', 1)
            vsize = tx_data.get('vsize', size)  # Virtual size for SegWit
            weight = tx_data.get('weight', size * 4)
            
            fee_rate_kvb = (fee / vsize) * 1000 if vsize > 0 else 0
            fee_rate_sat_vb = fee / vsize if vsize > 0 else 0
            
            return {
                'fee': fee,
                'size': size,
                'vsize': vsize,
                'weight': weight,
                'fee_rate_sat_kvb': fee_rate_kvb,
                'fee_rate_sat_vb': fee_rate_sat_vb
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing transaction fees: {e}")
            return {}
    
    def get_transaction_summary(self, tx_data: Dict) -> Dict[str, Any]:
        """Get a summary of transaction details relevant to RBF"""
        try:
            return {
                'txid': tx_data.get('txid', 'unknown'),
                'version': tx_data.get('version', 1),
                'locktime': tx_data.get('locktime', 0),
                'input_count': len(tx_data.get('vin', [])),
                'output_count': len(tx_data.get('vout', [])),
                'total_output_value': sum(
                    output.get('value', 0) for output in tx_data.get('vout', [])
                ),
                'is_segwit': any(
                    'witness' in vin for vin in tx_data.get('vin', [])
                ),
                'status': tx_data.get('status', {})
            }
            
        except Exception as e:
            self.logger.error(f"Error getting transaction summary: {e}")
            return {'txid': tx_data.get('txid', 'unknown')}
    
    def analyze_transaction(self, tx_data: Dict) -> Dict[str, Any]:
        """
        Comprehensive analysis of a transaction for RBF capabilities
        """
        try:
            # Check for BIP 125 signaling
            rbf_analysis = self.check_bip125_signaling(tx_data)
            
            # Analyze fees
            fee_analysis = self.analyze_transaction_fees(tx_data)
            
            # Get transaction summary
            tx_summary = self.get_transaction_summary(tx_data)
            
            # Combine all analysis
            result = {
                **rbf_analysis,
                'fee_analysis': fee_analysis,
                'transaction_summary': tx_summary,
                'analysis_timestamp': tx_data.get('status', {}).get('block_time')
            }
            
            if rbf_analysis.get('is_rbf'):
                self.logger.info(f"RBF transaction detected: {tx_summary.get('txid')} "
                               f"(fee rate: {fee_analysis.get('fee_rate_sat_vb', 0):.2f} sat/vB)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing transaction: {e}")
            return {
                'is_rbf': False,
                'error': str(e),
                'transaction_summary': {'txid': tx_data.get('txid', 'unknown')}
            }
