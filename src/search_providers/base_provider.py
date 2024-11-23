from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseSearchProvider(ABC):
    """
    Abstract base class for search providers.
    All search providers must implement these methods.
    """
    
    @abstractmethod
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the search provider.
        
        Args:
            api_key: Optional API key for the search provider
        """
        pass
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform a search using the provider.
        
        Args:
            query: The search query string
            **kwargs: Additional search parameters specific to the provider
            
        Returns:
            Dict containing the search results or error information
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the provider is properly configured (e.g., has valid API key).
        
        Returns:
            bool indicating if the provider is ready to use
        """
        pass
