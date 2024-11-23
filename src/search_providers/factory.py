"""Factory for creating search providers based on configuration."""

from typing import Type, Dict, Any
from search_providers.base_provider import BaseSearchProvider
from search_providers.bing_provider import BingSearchProvider
from search_providers.brave_provider import BraveSearchProvider
from search_providers.exa_provider import ExaSearchProvider
from search_providers.tavily_provider import TavilySearchProvider
from system_config import get_search_config

class SearchProviderFactory:
    """
    Factory class for creating instances of search providers.
    """

    _providers: Dict[str, Type[BaseSearchProvider]] = {
        "bing": BingSearchProvider,
        "brave": BraveSearchProvider,
        "exa": ExaSearchProvider,
        "tavily": TavilySearchProvider,
    }

    @classmethod
    def get_provider(cls, provider_type: str, **kwargs) -> BaseSearchProvider:
        """
        Get an instance of the specified search provider.

        Args:
            provider_type: The type of search provider to create (e.g., "bing", "google").
            **kwargs: Additional keyword arguments to pass to the provider's constructor.

        Returns:
            An instance of the requested search provider, or None if the provider type is invalid.
        """
        provider_class = cls._providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Invalid search provider type: {provider_type}")

        return provider_class(**kwargs)

    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[BaseSearchProvider]]:
        """
        Get a dictionary of available search provider types and their corresponding classes.

        Returns:
            A dictionary where keys are provider types (e.g., "bing", "google") and values are
            the corresponding search provider classes.
        """
        return cls._providers
