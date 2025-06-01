class SharedArchitectureError(Exception):
    """
    Base exception for all shared architecture related errors.
    """
    pass


class ConfigurationError(SharedArchitectureError):
    """
    Raised when there is a configuration issue.
    """
    pass


class ConnectionError(SharedArchitectureError):
    """
    Raised when a service connection fails.
    """
    pass


class ValidationError(SharedArchitectureError):
    """
    Raised when data validation fails.
    """
    pass


class RetryLimitExceededError(SharedArchitectureError):
    """
    Raised when retry attempts are exhausted.
    """
    pass


class BatchProcessingError(SharedArchitectureError):
    """
    Raised when a batch processing operation fails.
    """
    pass


class UnsupportedOperationError(SharedArchitectureError):
    """
    Raised when an unsupported operation is requested.
    """
    pass
