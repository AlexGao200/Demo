class RateLimitError(Exception):
    """Custom exception for rate limit errors"""

    pass


class TimeoutError(Exception):
    """Custom exception for timeout errors"""

    pass


class ProviderError(Exception):
    """Base class for provider-specific errors"""

    pass


class ConnectionError(ProviderError):
    """Error for network/connection issues"""

    pass


class AuthenticationError(ProviderError):
    """Error for authentication failures"""

    pass


class InvalidRequestError(ProviderError):
    """Error for malformed requests"""

    pass
