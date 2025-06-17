# shared_architecture/utils/symbol_converter.py
import logging
from typing import Dict, List, Optional, Any
from shared_architecture.utils.instrument_key_helper import (
    symbol_to_instrument_key,
    instrument_key_to_symbol
)

logger = logging.getLogger(__name__)

class SymbolConverter:
    """
    Handles consistent conversion between internal instrument_key format 
    and AutoTrader symbol format throughout the system.
    
    Internal Format (instrument_key): NSE@RELIANCE@equities
    AutoTrader Format (symbol): RELIANCE
    """
    
    @staticmethod
    def convert_to_autotrader_request(data: Dict, fields_to_convert: List[str] = None) -> Dict:
        """
        Convert internal data structure to AutoTrader request format.
        Converts instrument_key fields to symbol fields.
        
        Args:
            data: Dictionary containing internal data
            fields_to_convert: List of field names to convert (default: ['instrument_key'])
        
        Returns:
            Dictionary with AutoTrader-compatible symbol format
        """
        if fields_to_convert is None:
            fields_to_convert = ['instrument_key']
        
        converted_data = data.copy()
        
        for field in fields_to_convert:
            if field in converted_data and converted_data[field]:
                try:
                    instrument_key = converted_data[field]
                    symbol = instrument_key_to_symbol(instrument_key)
                    
                    # Replace instrument_key with symbol
                    if field == 'instrument_key':
                        converted_data['symbol'] = symbol
                        del converted_data['instrument_key']
                    else:
                        converted_data[field] = symbol
                        
                    logger.debug(f"Converted {field}: {instrument_key} -> {symbol}")
                    
                except Exception as e:
                    logger.error(f"Failed to convert {field} '{converted_data[field]}': {e}")
                    # Keep original value if conversion fails
        
        return converted_data
    
    @staticmethod
    def convert_from_autotrader_response(data: Dict, exchange: str = None) -> Dict:
        """
        Convert AutoTrader response to internal format.
        Converts symbol fields to instrument_key fields.
        
        Args:
            data: Dictionary containing AutoTrader response data
            exchange: Exchange name (if not in data)
        
        Returns:
            Dictionary with internal instrument_key format
        """
        converted_data = data.copy()
        
        # Extract exchange from data or use provided
        data_exchange = data.get('exchange') or exchange
        
        if 'symbol' in converted_data and converted_data['symbol']:
            try:
                symbol = converted_data['symbol']
                
                if data_exchange:
                    instrument_key = symbol_to_instrument_key(symbol, data_exchange)
                    converted_data['instrument_key'] = instrument_key
                    logger.debug(f"Converted symbol: {symbol} -> {instrument_key}")
                else:
                    logger.warning(f"No exchange provided for symbol {symbol}")
                    
            except Exception as e:
                logger.error(f"Failed to convert symbol '{converted_data['symbol']}': {e}")
        
        return converted_data
    
    @staticmethod
    def convert_autotrader_list_response(
        data_list: List[Any], 
        exchange_field: str = 'exchange'
    ) -> List[Dict]:
        """
        Convert list of AutoTrader objects/dicts to internal format.
        
        Args:
            data_list: List of AutoTrader response objects
            exchange_field: Field name containing exchange info
        
        Returns:
            List of dictionaries with instrument_key format
        """
        converted_list = []
        
        for item in data_list:
            try:
                # Convert object to dict if needed
                if hasattr(item, '__dict__'):
                    item_dict = {}
                    for key, value in item.__dict__.items():
                        if not key.startswith('_'):
                            item_dict[key] = value
                else:
                    item_dict = item if isinstance(item, dict) else {}
                
                # Get exchange from item
                exchange = item_dict.get(exchange_field)
                
                # Convert to internal format
                converted_item = SymbolConverter.convert_from_autotrader_response(
                    item_dict, exchange
                )
                converted_list.append(converted_item)
                
            except Exception as e:
                logger.error(f"Failed to convert AutoTrader item: {e}")
                # Include original item with error flag
                converted_list.append({
                    'conversion_error': str(e),
                    'original_data': str(item)
                })
        
        return converted_list
    
    @staticmethod
    def ensure_instrument_key_consistency(data: Dict) -> Dict:
        """
        Ensure instrument_key exists and is consistent with symbol/exchange.
        
        Args:
            data: Dictionary that may contain symbol, exchange, instrument_key
        
        Returns:
            Dictionary with consistent instrument_key
        """
        if 'instrument_key' in data and data['instrument_key']:
            # instrument_key exists, ensure symbol is consistent
            try:
                symbol = instrument_key_to_symbol(data['instrument_key'])
                data['symbol'] = symbol
            except Exception as e:
                logger.error(f"Failed to derive symbol from instrument_key: {e}")
        
        elif 'symbol' in data and 'exchange' in data:
            # Create instrument_key from symbol and exchange
            try:
                instrument_key = symbol_to_instrument_key(data['symbol'], data['exchange'])
                data['instrument_key'] = instrument_key
            except Exception as e:
                logger.error(f"Failed to create instrument_key from symbol/exchange: {e}")
        
        return data
    
    @staticmethod
    def validate_conversion(original_data: Dict, converted_data: Dict) -> bool:
        """
        Validate that conversion maintained data integrity.
        
        Args:
            original_data: Original data before conversion
            converted_data: Data after conversion
        
        Returns:
            True if conversion is valid
        """
        try:
            # Check if essential fields are preserved
            essential_fields = ['quantity', 'price', 'trade_type', 'pseudo_account']
            
            for field in essential_fields:
                if field in original_data:
                    if original_data[field] != converted_data.get(field):
                        logger.error(f"Conversion changed essential field {field}")
                        return False
            
            # Check if instrument identification is consistent
            if 'symbol' in original_data and 'instrument_key' in converted_data:
                # Reverse conversion to validate
                back_converted_symbol = instrument_key_to_symbol(converted_data['instrument_key'])
                if back_converted_symbol != original_data['symbol']:
                    logger.error(f"Symbol conversion inconsistent: {original_data['symbol']} != {back_converted_symbol}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Conversion validation failed: {e}")
            return False

class AutoTraderAdapter:
    """
    Adapter class that handles all AutoTrader interactions with proper symbol conversion.
    """
    
    def __init__(self, autotrader_connection):
        self.connection = autotrader_connection
    
    def place_regular_order(self, **kwargs) -> Dict:
        """Place regular order with automatic conversion"""
        # Convert internal format to AutoTrader format
        autotrader_request = SymbolConverter.convert_to_autotrader_request(kwargs)
        
        logger.info(f"Sending to AutoTrader: {autotrader_request}")
        
        # Call AutoTrader
        response = self.connection.place_regular_order(**autotrader_request)
        
        # Convert response back to internal format
        if response.success():
            converted_result = SymbolConverter.convert_from_autotrader_response(
                response.result, kwargs.get('exchange')
            )
            return {
                'success': True,
                'result': converted_result,
                'message': response.message
            }
        else:
            return {
                'success': False,
                'message': response.message
            }
    
    def read_platform_positions(self, pseudo_account: str) -> Dict:
        """Read positions with automatic conversion"""
        response = self.connection.read_platform_positions(pseudo_account)
        
        if response.success():
            converted_results = SymbolConverter.convert_autotrader_list_response(
                response.result, 'exchange'
            )
            return {
                'success': True,
                'result': converted_results,
                'message': response.message
            }
        else:
            return {
                'success': False,
                'message': response.message,
                'result': []
            }
    
    def read_platform_holdings(self, pseudo_account: str) -> Dict:
        """Read holdings with automatic conversion"""
        response = self.connection.read_platform_holdings(pseudo_account)
        
        if response.success():
            converted_results = SymbolConverter.convert_autotrader_list_response(
                response.result, 'exchange'
            )
            return {
                'success': True,
                'result': converted_results,
                'message': response.message
            }
        else:
            return {
                'success': False,
                'message': response.message,
                'result': []
            }
    
    def read_platform_orders(self, pseudo_account: str) -> Dict:
        """Read orders with automatic conversion"""
        response = self.connection.read_platform_orders(pseudo_account)
        
        if response.success():
            converted_results = SymbolConverter.convert_autotrader_list_response(
                response.result, 'exchange'
            )
            return {
                'success': True,
                'result': converted_results,
                'message': response.message
            }
        else:
            return {
                'success': False,
                'message': response.message,
                'result': []
            }
    
    def read_platform_margins(self, pseudo_account: str) -> Dict:
        """Read margins (no conversion needed)"""
        response = self.connection.read_platform_margins(pseudo_account)
        
        if response.success():
            # Margins don't have symbols, so no conversion needed
            results = []
            for margin in response.result:
                if hasattr(margin, '__dict__'):
                    margin_dict = {}
                    for key, value in margin.__dict__.items():
                        if not key.startswith('_'):
                            margin_dict[key] = value
                    results.append(margin_dict)
                else:
                    results.append(margin)
            
            return {
                'success': True,
                'result': results,
                'message': response.message
            }
        else:
            return {
                'success': False,
                'message': response.message,
                'result': []
            }