# shared_architecture/utils/instrument_key_helper.py
from datetime import datetime
import re
from typing import Tuple, Optional

def get_instrument_key(
    exchange: str,
    stock_code: str,
    product_type: str,
    expiry_date: Optional[str] = None,  # Fix: Use Optional[str] instead of str = None
    option_type: Optional[str] = None,  # Fix: Use Optional[str] instead of str = None
    strike_price: Optional[str] = None  # Fix: Use Optional[str] instead of str = None
) -> str:
    """
    Generate a unique instrument key for equities, futures, and options.
    Special rule: If option_type == 'xx', treat as futures (ignore option_type/strike_price).
    
    Args:
        exchange: Exchange name (e.g., 'NSE', 'BSE')
        stock_code: Stock/underlying code (e.g., 'RELIANCE', 'NIFTY')
        product_type: Product type ('equities', 'futures', 'options', 'bonds')
        expiry_date: Expiry date in format "DD-MMM-YYYY" (e.g., "25-JUN-2025")
        option_type: Option type ('call', 'put', 'xx')
        strike_price: Strike price as string
    
    Returns:
        str: Internal instrument_key format
    """
    
    # Safely handle None values
    product_type = (product_type or "").strip().lower()
    option_type = (option_type or "").strip().lower()
    exchange = (exchange or "").strip().upper()
    stock_code = (stock_code or "").strip().upper()
    
    if product_type == "equities":
        return f"{exchange}@{stock_code}@equities"
    
    elif product_type == "futures":
        if not expiry_date:
            raise ValueError("expiry_date is required for futures")
        return f"{exchange}@{stock_code}@futures@{expiry_date}"
    
    elif product_type == "options":
        if option_type == "xx":
            # Treat like a future: drop option_type and strike_price
            if not expiry_date:
                raise ValueError("expiry_date is required for options with option_type='xx'")
            return f"{exchange}@{stock_code}@futures@{expiry_date}"
        
        # Normal options
        if not all([expiry_date, option_type, strike_price]):
            raise ValueError("expiry_date, option_type, and strike_price are required for options")
        return f"{exchange}@{stock_code}@options@{expiry_date}@{option_type}@{strike_price}"
    
    elif product_type == "bonds":
        return f"{exchange}@{stock_code}@bonds"
    
    else:
        raise ValueError(f"Unsupported product type: {product_type}")


def symbol_to_instrument_key(symbol: str, exchange: str = 'NSE') -> str:
    """
    Convert AutoTrader/StocksDeveloper symbol to internal instrument_key.
    
    This function handles INBOUND traffic from AutoTrader API responses.
    
    Args:
        symbol: AutoTrader symbol format (e.g., "RELIANCE", "NIFTY25JUNFUT", "NIFTY25JUN25100CE")
        exchange: Exchange name (default: 'NSE')
    
    Returns:
        str: Internal instrument_key format (e.g., "NSE@RELIANCE@equities", "NSE@NIFTY@futures@25-JUN-2025")
    
    Examples:
        symbol_to_instrument_key("RELIANCE") -> "NSE@RELIANCE@equities"
        symbol_to_instrument_key("NIFTY25JUNFUT") -> "NSE@NIFTY@futures@25-JUN-2025"
        symbol_to_instrument_key("NIFTY25JUN25100CE") -> "NSE@NIFTY@options@25-JUN-2025@call@25100"
        symbol_to_instrument_key("846REC28") -> "NSE@REC@bonds"
    """
    
    if not symbol or not isinstance(symbol, str):
        return f"{exchange}@UNKNOWN@equities"
    
    symbol = symbol.strip().upper()
    
    try:
        # Check for bonds
        if _is_bond_symbol(symbol):
            stock_code = _extract_bond_stock_code(symbol)
            return get_instrument_key(exchange, stock_code, "bonds")
        
        # Check for futures
        if symbol.endswith('FUT'):
            stock_code, expiry_date = _parse_futures_symbol(symbol)
            return get_instrument_key(exchange, stock_code, "futures", expiry_date)
        
        # Check for options
        if symbol.endswith(('CE', 'PE')):
            stock_code, expiry_date, option_type, strike_price = _parse_options_symbol(symbol)
            return get_instrument_key(exchange, stock_code, "options", expiry_date, option_type, strike_price)
        
        # Default to equities
        if not any(char.isdigit() for char in symbol):
            return get_instrument_key(exchange, symbol, "equities")
        
        # Fallback
        stock_code = re.sub(r'\d+.*$', '', symbol)
        if not stock_code:
            stock_code = symbol
        return get_instrument_key(exchange, stock_code, "equities")
        
    except Exception as e:
        print(f"ERROR: Failed to parse symbol '{symbol}': {e}")
        return get_instrument_key(exchange, symbol, "equities")


def instrument_key_to_symbol(instrument_key: str) -> str:
    """
    Convert internal instrument_key to AutoTrader/StocksDeveloper symbol format.
    
    This function handles OUTBOUND traffic to AutoTrader API calls.
    
    Args:
        instrument_key: Internal format "exchange@stock_code@product_type@expiry_date@option_type@strike_price"
    
    Returns:
        str: AutoTrader symbol format
    
    Examples:
        instrument_key_to_symbol("NSE@RELIANCE@equities") -> "RELIANCE"
        instrument_key_to_symbol("NSE@NIFTY@futures@25-JUN-2025") -> "NIFTY25JUNFUT"
        instrument_key_to_symbol("NSE@NIFTY@options@25-JUN-2025@call@25100") -> "NIFTY25JUN25100CE"
    """
    parts = instrument_key.split('@')
    if len(parts) < 3:
        return parts[1] if len(parts) > 1 else instrument_key
    
    exchange, stock_code, product_type = parts[0], parts[1], parts[2]
    
    # Equities: just return stock_code
    if product_type == "equities":
        return stock_code
    
    # Bonds: just return stock_code (AutoTrader handles bond symbols differently)
    elif product_type == "bonds":
        return stock_code
    
    # Futures: stock_code + expiry + "FUT"
    elif product_type == "futures" and len(parts) >= 4:
        expiry_date = parts[3]  # "25-JUN-2025"
        # Convert "25-JUN-2025" to "25JUNFUT"
        if expiry_date:
            day_month = expiry_date.split('-')[:2]  # ["25", "JUN"]
            return f"{stock_code}{''.join(day_month)}FUT"  # "NIFTY25JUNFUT"
    
    # Options: stock_code + expiry + strike + CE/PE
    elif product_type == "options" and len(parts) >= 6:
        expiry_date, option_type, strike_price = parts[3], parts[4], parts[5]
        if expiry_date and option_type and strike_price:
            day_month = expiry_date.split('-')[:2]  # ["25", "JUN"]
            ce_pe = "CE" if option_type == "call" else "PE"
            return f"{stock_code}{''.join(day_month)}{strike_price}{ce_pe}"
    
    # Fallback
    return stock_code


def _is_bond_symbol(symbol: str) -> bool:
    """Check if symbol is a bond (starts and ends with numbers)."""
    return (len(symbol) > 2 and 
            symbol[0].isdigit() and 
            symbol[-1].isdigit() and 
            symbol[-2].isdigit())


def _extract_bond_stock_code(symbol: str) -> str:
    """Extract stock code from bond symbol."""
    # Remove leading numbers and trailing numbers
    # Examples: 846REC28 -> REC, 850NHAI29 -> NHAI
    match = re.search(r'^\d+([A-Z]+)\d+$', symbol)
    if match:
        stock_code = match.group(1)
        # Handle special cases where company names might be abbreviated
        if stock_code == 'PFCL':
            return 'PFC'
        return stock_code
    
    # Fallback: remove all numbers
    return re.sub(r'\d+', '', symbol)


def _parse_futures_symbol(symbol: str) -> Tuple[str, str]:
    """Parse futures symbol to extract stock_code and expiry_date."""
    # Remove 'FUT' suffix
    base_symbol = symbol[:-3]
    
    # Find first digit position
    first_digit_pos = next((i for i, char in enumerate(base_symbol) if char.isdigit()), None)
    
    if first_digit_pos is None:
        raise ValueError(f"No digits found in futures symbol: {symbol}")
    
    stock_code = base_symbol[:first_digit_pos]
    date_part = base_symbol[first_digit_pos:]
    
    expiry_date = _parse_expiry_date(date_part)
    return stock_code, expiry_date


def _parse_options_symbol(symbol: str) -> Tuple[str, str, str, str]:
    """Parse options symbol to extract all components."""
    # Remove CE/PE suffix
    option_type = 'call' if symbol.endswith('CE') else 'put'
    base_symbol = symbol[:-2]
    
    # Find first digit position
    first_digit_pos = next((i for i, char in enumerate(base_symbol) if char.isdigit()), None)
    
    if first_digit_pos is None:
        raise ValueError(f"No digits found in options symbol: {symbol}")
    
    stock_code = base_symbol[:first_digit_pos]
    date_and_strike = base_symbol[first_digit_pos:]
    
    # Parse expiry date (first 5-6 characters: day + month)
    expiry_date, remaining = _parse_expiry_date_with_remainder(date_and_strike)
    
    # Remaining part is strike price
    strike_price = remaining if remaining else "0"
    
    return stock_code, expiry_date, option_type, strike_price


def _parse_expiry_date(date_str: str) -> str:
    """Parse expiry date from string like '25JUN'."""
    if len(date_str) < 5:
        raise ValueError(f"Invalid date string: {date_str}")
    
    # Extract day (first 2 digits) and month (next 3 characters)
    day_str = date_str[:2]
    month_str = date_str[2:5]
    
    day = int(day_str)
    year = _determine_year(day, month_str)
    
    return f"{day:02d}-{month_str}-{year}"


def _parse_expiry_date_with_remainder(date_str: str) -> Tuple[str, str]:
    """Parse expiry date and return remaining string."""
    if len(date_str) < 5:
        raise ValueError(f"Invalid date string: {date_str}")
    
    # Extract day (first 2 digits) and month (next 3 characters)
    day_str = date_str[:2]
    month_str = date_str[2:5]
    remaining = date_str[5:]  # Rest is strike price
    
    day = int(day_str)
    year = _determine_year(day, month_str)
    
    expiry_date = f"{day:02d}-{month_str}-{year}"
    return expiry_date, remaining


def _determine_year(day: int, month_str: str) -> int:
    """Determine year based on current date logic."""
    month_mapping = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    
    if month_str not in month_mapping:
        raise ValueError(f"Invalid month: {month_str}")
    
    month = month_mapping[month_str]
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    current_day = current_date.day
    
    # Year logic: If month > current month OR (month == current month AND day >= current day) 
    # → current year, else next year
    if month > current_month or (month == current_month and day >= current_day):
        return current_year
    else:
        return current_year + 1


def parse_stocksdeveloper_symbol(symbol: str, exchange: str = 'NSE') -> dict:
    """
    Parse AutoTrader symbol format and return instrument key components.
    
    Args:
        symbol: AutoTrader symbol (e.g., "RELIANCE", "NIFTY25JUNFUT", "NIFTY25JUN24000CE")
        exchange: Exchange name (default: NSE)
    
    Returns:
        dict with instrument_key components
    """
    
    # Always treat symbols as equity unless they match specific F&O patterns
    # This prevents the "No digits found in options symbol" error
    
    # Check for futures pattern: NIFTY25JUNFUT, BANKNIFTY25JUNFUT, etc.
    import re
    fut_pattern = r'^([A-Z]+)(\d{2})([A-Z]{3})FUT$'
    fut_match = re.match(fut_pattern, symbol)
    if fut_match:
        base_symbol, day, month = fut_match.groups()
        return {
            'instrument_key': f"{exchange}@{symbol}@futures@{day}-{month}-2025",
            'exchange': exchange,
            'stock_code': base_symbol,
            'product_type': 'futures',
            'expiry_date': f"{day}-{month}-2025",
            'option_type': None,
            'strike_price': None
        }
    
    # Check for options pattern: NIFTY25JUN24000CE, NIFTY25JUN24000PE, etc.
    opt_pattern = r'^([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)$'
    opt_match = re.match(opt_pattern, symbol)
    if opt_match:
        base_symbol, day, month, strike, option_type = opt_match.groups()
        return {
            'instrument_key': f"{exchange}@{symbol}@options@{day}-{month}-2025@{option_type}@{strike}",
            'exchange': exchange,
            'stock_code': base_symbol,
            'product_type': 'options',
            'expiry_date': f"{day}-{month}-2025",
            'option_type': option_type,
            'strike_price': strike
        }
    
    # Check for bonds pattern: starts and ends with numbers (e.g., 867PFCL33, 846REC28)
    if _is_bond_symbol(symbol):
        stock_code = _extract_bond_stock_code(symbol)
        return {
            'instrument_key': f"{exchange}@{stock_code}@bonds",
            'exchange': exchange,
            'stock_code': stock_code,
            'product_type': 'bonds',
            'expiry_date': None,
            'option_type': None,
            'strike_price': None
        }
    
    # Default case: treat everything else as equity (RELIANCE, TCS, HDFC, etc.)
    # Correct format: NSE@RELIANCE@equities (no extra @)
    return {
        'instrument_key': f"{exchange}@{symbol}@equities",
        'exchange': exchange,
        'stock_code': symbol,
        'product_type': 'equities',
        'expiry_date': None,
        'option_type': None,
        'strike_price': None
    }
# Test function
def test_instrument_key_generator():
    """Test the instrument key generator with various examples."""
    test_cases = [
        # Equities
        ("RELIANCE", "NSE@RELIANCE@equities"),
        ("HDFC", "NSE@HDFC@equities"),
        ("TCS", "NSE@TCS@equities"),
        
        # Bonds
        ("846REC28", "NSE@REC@bonds"),
        ("850NHAI29", "NSE@NHAI@bonds"),
        ("855IIFCL29", "NSE@IIFCL@bonds"),
        ("1015UPPC26", "NSE@UPPC@bonds"),
        ("867PFCL33", "NSE@PFC@bonds"),
        
        # Futures (assuming current date context)
        ("NIFTY25JUNFUT", "NSE@NIFTY@futures@25-JUN-2025"),
        ("BANKNIFTY15JULFUT", "NSE@BANKNIFTY@futures@15-JUL-2025"),
        
        # Options
        ("NIFTY25JUN25100CE", "NSE@NIFTY@options@25-JUN-2025@call@25100"),
        ("NIFTY25JUN24000PE", "NSE@NIFTY@options@25-JUN-2025@put@24000"),
        
        # Edge cases
        ("", "NSE@UNKNOWN@equities"),
        ("INVALID", "NSE@INVALID@equities"),
        ("123ABC", "NSE@ABC@equities"),  # Malformed but handled
    ]
    
    print("Testing Instrument Key Generator:")
    print("=" * 50)
    
    for symbol, expected in test_cases:
        result = symbol_to_instrument_key(symbol)
        status = "✓" if result == expected else "✗"
        print(f"{status} {symbol:15} -> {result}")
        if result != expected:
            print(f"    Expected: {expected}")
            print(f"    Got:      {result}")
    
    print("\n" + "=" * 50)

def test_symbol_parsing():
    """Test function to verify symbol parsing works correctly"""
    test_cases = [
        ("RELIANCE", "NSE", "NSE@RELIANCE@equities"),
        ("TCS", "BSE", "BSE@TCS@equities"),
        ("NIFTY25JUNFUT", "NSE", "NSE@NIFTY25JUNFUT@futures@25-JUN-2025"),
        ("BANKNIFTY25DECFUT", "NSE", "NSE@BANKNIFTY25DECFUT@futures@25-DEC-2025"),
        ("NIFTY25JUN24000CE", "NSE", "NSE@NIFTY25JUN24000CE@options@25-JUN-2025@CE@24000"),
        ("NIFTY25JUN24000PE", "NSE", "NSE@NIFTY25JUN24000PE@options@25-JUN-2025@PE@24000"),
    ]
    
    print("Testing symbol parsing:")
    for symbol, exchange, expected in test_cases:
        result = symbol_to_instrument_key(symbol, exchange)
        status = "✅" if result == expected else "❌"
        print(f"{status} {symbol} ({exchange}) -> {result}")
        if result != expected:
            print(f"   Expected: {expected}")

if __name__ == "__main__":
    test_instrument_key_generator()