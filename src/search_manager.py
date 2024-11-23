"""
SearchManager handles search provider selection, fallback, and result normalization.
"""
import logging
from typing import Dict, List, Any, Optional
from time import sleep

from .system_config import get_search_config
from .search_providers.factory import SearchProviderFactory

logger = logging.getLogger(__name__)

class SearchManager:
    """
    Manages multiple search providers with fallback support and result normalization.
    """
    
    def __init__(self, tavily_api_key=None, brave_api_key=None, bing_api_key=None, exa_api_key=None):
        """Initialize SearchManager with configuration and providers."""
        self.config = get_search_config()
        self.factory = SearchProviderFactory()
        self.providers = self._initialize_providers(tavily_api_key, brave_api_key, bing_api_key, exa_api_key)
        self.current_provider = self.config["default_provider"]
        
    def _initialize_providers(self, tavily_api_key=None, brave_api_key=None, bing_api_key=None, exa_api_key=None) -> Dict[str, Any]:
        """Initialize all configured search providers."""
        providers = {}
        for provider_name in self.config["fallback_order"]:
            try:
                if provider_name == 'tavily':
                    provider = self.factory.get_provider(provider_name, api_key=tavily_api_key)
                elif provider_name == 'brave':
                    provider = self.factory.get_provider(provider_name, api_key=brave_api_key)
                elif provider_name == 'bing':
                    provider = self.factory.get_provider(provider_name, api_key=bing_api_key)
                elif provider_name == 'exa':
                    provider = self.factory.get_provider(provider_name, api_key=exa_api_key)
                else:
                    provider = self.factory.get_provider(provider_name)

                if provider.is_configured():
                    providers[provider_name] = provider
                    logger.info(f"Successfully initialized {provider_name} provider")
                else:
                    logger.warning(f"Provider {provider_name} not properly configured")
            except Exception as e:
                logger.error(f"Failed to initialize {provider_name} provider: {str(e)}")
        return providers
    
    def _normalize_results(self, results: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """
        Normalize search results to a standard format regardless of provider.
        
        Standard format:
        {
            'success': bool,
            'error': Optional[str],
            'results': List[{
                'title': str,
                'url': str,
                'content': str,
                'score': float,
                'published_date': Optional[str]
            }],
            'answer': Optional[str],  # For providers that support AI-generated answers
            'provider': str
        }
        """
        if not isinstance(results, dict):
            return {
                'success': False,
                'error': f'Invalid results format from {provider}',
                'results': [],
                'provider': provider
            }
            
        if 'error' in results:
            return {
                'success': False,
                'error': results['error'],
                'results': [],
                'provider': provider
            }
            
        normalized = {
            'success': True,
            'error': None,
            'provider': provider,
            'results': []
        }
        
        # Handle Tavily's AI answer if present
        if 'answer' in results:
            normalized['answer'] = results['answer']
            
        # Normalize results based on provider
        if provider == 'tavily':
            # Handle both general and news results from Tavily
            if 'articles' in results:
                normalized['results'] = [{
                    'title': r.get('title', ''),
                    'url': r.get('url', ''),
                    'content': r.get('content', '')[:500],
                    'score': float(r.get('score', 0.0)),
                    'published_date': r.get('published_date')
                } for r in results.get('articles', [])]
            else:
                normalized['results'] = results.get('results', [])
        elif provider == 'brave':
            normalized['results'] = [{
                'title': r.get('title', ''),
                'url': r.get('url', ''),
                'content': r.get('description', '')[:500],
                'score': float(r.get('relevance_score', 0.0)),
                'published_date': r.get('published_date')
            } for r in results.get('results', [])]
        elif provider == 'bing':
            normalized['results'] = [{
                'title': r.get('title', ''),
                'url': r.get('url', ''),
                'content': r.get('content', '')[:500],
                'score': 1.0,  # Bing doesn't provide relevance scores
                'published_date': None
            } for r in results.get('results', [])]
        elif provider == 'exa':
            normalized['results'] = [{
                'title': r.get('title', ''),
                'url': r.get('url', ''),
                'content': r.get('text', '')[:500],
                'score': float(r.get('relevance_score', 0.0)),
                'published_date': r.get('published_date')
            } for r in results.get('results', [])]
        elif provider == 'duckduckgo':
            if not isinstance(results, list):
                results = []
            normalized['results'] = [{
                'title': r.get('title', ''),
                'url': r.get('link', ''),
                'content': r.get('snippet', '')[:500],
                'score': 1.0,  # DuckDuckGo doesn't provide relevance scores
                'published_date': None
            } for r in results]
            
        return normalized
    
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform a search using configured providers with fallback support.
        """
        tried_providers = set()
        
        # First try the default provider
        if self.current_provider in self.providers:
            try:
                provider = self.providers[self.current_provider]
                provider_settings = self.config["provider_settings"].get(self.current_provider, {})
                search_params = {**provider_settings, **kwargs}
                
                results = provider.search(query, **search_params)
                normalized_results = self._normalize_results(results, self.current_provider)
                
                if normalized_results['success']:
                    return normalized_results
                    
                logger.warning(
                    f"Search with default provider {self.current_provider} failed: {normalized_results.get('error')}"
                )
            except Exception as e:
                logger.error(f"Error using default provider {self.current_provider}: {str(e)}")
            
            tried_providers.add(self.current_provider)
        
        # Then try providers in fallback order
        for provider_name in self.config["fallback_order"]:
            if provider_name not in self.providers or provider_name in tried_providers:
                continue
                
            tried_providers.add(provider_name)
            provider = self.providers[provider_name]
            
            try:
                # Get provider-specific settings
                provider_settings = self.config["provider_settings"].get(provider_name, {})
                search_params = {**provider_settings, **kwargs}
                
                # Perform search
                results = provider.search(query, **search_params)
                normalized_results = self._normalize_results(results, provider_name)
                
                # If search was successful, update current provider and return results
                if normalized_results['success']:
                    self.current_provider = provider_name
                    return normalized_results
                    
                logger.warning(
                    f"Search with {provider_name} failed: {normalized_results.get('error')}"
                )
                
            except Exception as e:
                logger.error(f"Error using {provider_name} provider: {str(e)}")
                
            # Apply rate limiting before trying next provider
            sleep(self.config["rate_limiting"]["cooldown_period"] / len(self.providers))
            
        # If all providers failed, return error
        return {
            'success': False,
            'error': 'All search providers failed',
            'results': [],
            'provider': None
        }
    
    def get_current_provider(self) -> str:
        """Get the name of the currently active search provider."""
        return self.current_provider
    
    def get_available_providers(self) -> List[str]:
        """Get list of available (properly configured) search providers."""
        return list(self.providers.keys())
