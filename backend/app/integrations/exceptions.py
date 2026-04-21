class IntegrationError(Exception):
    """Base class for all integration-related errors."""
    pass

class TokenExpiredError(IntegrationError):
    """Raised when an access token has naturally expired (HTTP 401)."""
    pass

class TokenRevokedError(IntegrationError):
    """Raised when refresh token is denied or revoked by the user."""
    pass

class MissingScopeError(IntegrationError):
    """Raised when the provider denies action due to lack of authorization scopes (HTTP 403)."""
    pass

class ProviderAPIError(IntegrationError):
    """Raised for any unexpected provider degradation (HTTP 500, Rate limits)."""
    pass

class IntegrationNotAttachedError(IntegrationError):
    """Raised when the workspace has no integration stored."""
    pass
