"""Instrument parsing utilities for Vortex CLI."""

from pathlib import Path
from typing import List, Optional, Tuple


def parse_instruments(symbols: Tuple[str, ...], symbols_file: Optional[Path]) -> List[str]:
    """Parse instruments from command line arguments and/or file.
    
    Args:
        symbols: Tuple of symbols from command line
        symbols_file: Optional path to file containing symbols
    
    Returns:
        List of unique symbol strings
    """
    all_symbols = []
    
    # Add symbols from command line
    all_symbols.extend(symbols)
    
    # Add symbols from file if provided
    if symbols_file:
        file_symbols = load_symbols_from_file(symbols_file)
        all_symbols.extend(file_symbols)
    
    # Remove duplicates while preserving order
    unique_symbols = []
    seen = set()
    
    for symbol in all_symbols:
        symbol_upper = symbol.upper().strip()
        if symbol_upper and symbol_upper not in seen:
            unique_symbols.append(symbol_upper)
            seen.add(symbol_upper)
    
    return unique_symbols


def load_symbols_from_file(file_path: Path) -> List[str]:
    """Load symbols from a text file.
    
    Args:
        file_path: Path to file containing symbols
    
    Returns:
        List of symbols from file
    
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read
    """
    symbols = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Handle comma-separated values on same line
                if ',' in line:
                    line_symbols = [s.strip() for s in line.split(',')]
                    symbols.extend(line_symbols)
                else:
                    symbols.append(line)
                    
    except FileNotFoundError:
        raise FileNotFoundError(f"Symbols file not found: {file_path}")
    except IOError as e:
        raise IOError(f"Error reading symbols file {file_path}: {e}")
    
    return [s for s in symbols if s]  # Remove empty strings


def validate_symbol(symbol: str) -> bool:
    """Validate a symbol format.
    
    Args:
        symbol: Symbol string to validate
    
    Returns:
        True if symbol appears valid, False otherwise
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    symbol = symbol.strip().upper()
    
    # Basic validation - alphanumeric with some special chars
    if not symbol:
        return False
    
    # Allow letters, numbers, and common separators
    allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/')
    
    return all(c in allowed_chars for c in symbol)


def normalize_symbol(symbol: str) -> str:
    """Normalize a symbol to standard format.
    
    Args:
        symbol: Raw symbol string
    
    Returns:
        Normalized symbol string
    """
    if not symbol:
        return ""
    
    # Convert to uppercase and strip whitespace
    normalized = symbol.strip().upper()
    
    # Handle common format variations
    # Example: convert "gc-feb25" to "GCG25"
    # This would need to be customized based on your specific requirements
    
    return normalized


def detect_instrument_type(symbol: str) -> str:
    """Detect the likely instrument type based on symbol format.
    
    Args:
        symbol: Symbol to analyze
    
    Returns:
        Instrument type: 'future', 'stock', 'forex', or 'unknown'
    """
    if not symbol:
        return 'unknown'
    
    symbol = symbol.upper().strip()
    
    # Futures often have month/year codes
    if len(symbol) >= 5 and symbol[-2:].isdigit():
        # Check if it has a month code before the year
        month_codes = set('FGHJKMNQUVXZ')  # Standard futures month codes
        if len(symbol) >= 3 and symbol[-3] in month_codes:
            return 'future'
    
    # Forex pairs often have forward slash or underscore
    if '/' in symbol or '_' in symbol:
        parts = symbol.replace('_', '/').split('/')
        if len(parts) == 2 and len(parts[0]) == 3 and len(parts[1]) == 3:
            return 'forex'
    
    # Stock symbols are usually 1-5 characters
    if 1 <= len(symbol) <= 5 and symbol.isalpha():
        return 'stock'
    
    return 'unknown'


def expand_symbol_patterns(symbols: List[str]) -> List[str]:
    """Expand symbol patterns and wildcards.
    
    Args:
        symbols: List of symbols that may contain patterns
    
    Returns:
        Expanded list of symbols
    """
    expanded = []
    
    for symbol in symbols:
        if '*' in symbol or '?' in symbol:
            # Handle wildcard expansion
            # This would need to be implemented based on your specific needs
            # For now, just add the symbol as-is
            expanded.append(symbol)
        else:
            expanded.append(symbol)
    
    return expanded