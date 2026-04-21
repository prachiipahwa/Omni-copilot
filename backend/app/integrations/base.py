from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseConnector(ABC):
    """
    Abstract base class for all integrations to inherit from.
    Ensures unified contracts for authentication, sync, and orchestration.
    """
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for the connector (e.g., 'google_drive', 'slack')"""
        pass

    @abstractmethod
    async def get_auth_url(self, state: str) -> str:
        """Return the OAuth authorization URL"""
        pass

    @abstractmethod
    async def exchange_token(self, code: str) -> Dict[str, Any]:
        """Exchange auth code for tokens and normalize into a dictionary"""
        pass
        
    @abstractmethod
    async def refresh_credentials(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh invalid credentials and return normalized context."""
        pass

    @abstractmethod
    async def perform_search(self, query: str, credentials: Dict[str, Any], **kwargs) -> list[Dict[str, Any]]:
        """Search across the integration's resources"""
        pass

    @abstractmethod
    async def ingest_data(self, credentials: Dict[str, Any]) -> Any:
        """Background job hook to ingest data into vector store"""
        pass
