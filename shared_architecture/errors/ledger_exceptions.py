class LedgerProcessingError(Exception):
    """Base exception for ledger processing errors"""
    pass

class UnsupportedBrokerError(LedgerProcessingError):
    """Raised when broker is not supported"""
    pass

class LedgerFileParsingError(LedgerProcessingError):
    """Raised when ledger file cannot be parsed"""
    pass

class LedgerEntryValidationError(LedgerProcessingError):
    """Raised when ledger entry validation fails"""
    pass