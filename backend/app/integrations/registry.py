from typing import Dict, Type
from app.integrations.base import BaseConnector

class ConnectorRegistry:
    _registry: Dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, connector_class: Type[BaseConnector]):
        instance = connector_class()
        cls._registry[instance.provider_id] = connector_class
        return connector_class

    @classmethod
    def get_connector(cls, provider_id: str) -> BaseConnector:
        connector_class = cls._registry.get(provider_id)
        if not connector_class:
            raise ValueError(f"Connector {provider_id} not initialized or found.")
        return connector_class()

# Usage Example:
# @ConnectorRegistry.register
# class GoogleDriveConnector(BaseConnector):
#    ...
