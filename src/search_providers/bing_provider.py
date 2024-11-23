from typing import Dict, Any, Optional
import os
import sys
from pathlib import Path
import requests
from datetime import datetime, timedelta
import json

# Add parent directory to path for imports when running as script
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent))
    from search_providers.base_provider import BaseSearchProvider
else:
    from .base_provider import BaseSearchProvider

class BingSearchProvider(BaseSearchProvider):
    """
    Bing implementation of the search provider interface.
    Handles both web and news-specific searches using Bing's APIs.
    """
    
    WEB_SEARCH_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
    NEWS_SEARCH_ENDPOINT = "https://api.bing.microsoft.com/v7.0/news/search"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Bing search provider.
        
        Args:
            api_key: Optional Bing API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("BING_API_KEY")
        self.headers = {
            'Ocp-Apim-Subscription-Key': self.api_key,
            'Accept': 'application/json'
        } if self.api_key else None
        
        # Load trusted news sources
        self.trusted_sources = self._load_trusted_sources()
    
    def _load_trusted_sources(self) -> list:
        """Load first 5 trusted news sources from JSON file."""
        try:
            json_path = Path(__file__).parent / "trusted_news_sources.json"
            with open(json_path) as f:
                data = json.load(f)
                # Only load the first 16 sources as per MSFT limits
                return data.get("trusted_sources", [])[:16]
        except Exception as e:
            print(f"Warning: Could not load trusted news sources: {e}")
            return []
    
    def is_configured(self) -> bool:
        """Check if Bing API is properly configured."""
        return self.headers is not None
    
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform a search using Bing API.
        
        Args:
            query: The search query string
            **kwargs: Additional search parameters:
                - topic: Optional search topic (e.g., "news")
                - max_results: Maximum number of results (default: 10)
                - market: Market code (default: "en-US")
                - days: Number of days to look back (for news searches)
                
        Returns:
            Dict containing search results or error information
        """
        if not self.is_configured():
            return {'error': 'Bing API key not configured'}

        try:
            # Set default search parameters
            search_params = {
                'count': str(kwargs.get('max_results', 10)),  # Changed default from 5 to 10
                'mkt': kwargs.get('market', 'en-US'),
                'textFormat': 'Raw'
            }
            
            # Determine if this is a news search
            if kwargs.get('topic') == 'news':
                # Add freshness parameter for news if days specified
                if 'days' in kwargs:
                    # Bing API expects 'day', 'week', or 'month'
                    search_params['freshness'] = 'week' if kwargs['days'] >1 else 'day'
                
                # Add site: operators for trusted sources
                if self.trusted_sources:
                    site_operators = " OR ".join(f'site:{source}' for source in self.trusted_sources)
                    search_params['q'] = f"({query}) ({site_operators})"
                else:
                    search_params['q'] = f"latest headlines about the topic: {query}"
                
                response = requests.get(
                    self.NEWS_SEARCH_ENDPOINT,
                    headers=self.headers,
                    params=search_params
                )
            else:
                search_params['q'] = query
                response = requests.get(
                    self.WEB_SEARCH_ENDPOINT,
                    headers=self.headers,
                    params=search_params
                )

            if response.status_code != 200:
                return {'error': f'API request failed with status {response.status_code}: {response.text}'}
            
            response_data = response.json()
            
            # Process results based on search type
            if kwargs.get('topic') == 'news':
                return self._process_news_results(
                    response_data,
                    days=kwargs.get('days', 3),
                    topic=query
                )
            else:
                return self._process_general_results(response_data)
            
        except requests.exceptions.RequestException as e:
            return {'error': f'API request failed: {str(e)}'}
        except Exception as e:
            return {'error': f'An unexpected error occurred: {str(e)}'}
    
    def _process_general_results(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process results for general web searches."""
        webpages = response.get('webPages', {}).get('value', [])
        return {
            'results': [{
                'title': result.get('name', ''),
                'url': result.get('url', ''),
                'content': result.get('snippet', ''),
                'score': 1.0  # Bing doesn't provide relevance scores
            } for result in webpages[:10]]  # Changed from 3 to 10
        }
    
    def _process_news_results(self, response: Dict[str, Any], days: int, topic: str) -> Dict[str, Any]:
        """Process results for news-specific searches."""
        articles = response.get('value', [])
        return {
            'articles': [{
                'title': article.get('name', ''),
                'url': article.get('url', ''),
                'published_date': article.get('datePublished', ''),
                'content': article.get('description', ''),
                'score': 1.0  # Bing doesn't provide relevance scores
            } for article in articles],
            'time_period': f"Past {days} days",
            'topic': topic
        }

if __name__ == "__main__":
    # Test code using actual API
    provider = BingSearchProvider()
    if not provider.is_configured():
        print("Error: Bing API key not configured")
        exit(1)

    # Print loaded trusted sources
    print("\n=== Loaded Trusted Sources ===")
    print(provider.trusted_sources)

    # Test general search
    print("\n=== Testing General Search ===")
    general_result = provider.search(
        "What is artificial intelligence?",
        max_results=10  # Changed from 3 to 10
    )
    
    if 'error' in general_result:
        print(f"Error in general search: {general_result['error']}")
    else:
        print("\nTop Results:")
        for idx, result in enumerate(general_result['results'], 1):
            print(f"\n{idx}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Preview: {result['content'][:400]}...")

    # Test news search
    print("\n\n=== Testing News Search ===")
    news_result = provider.search(
        "mike tyson fight",
        topic="news",
        days=3
    )
    
    if 'error' in news_result:
        print(f"Error in news search: {news_result['error']}")
    else:
        print("\nRecent Articles:")
        for idx, article in enumerate(news_result['articles'], 1):
            print(f"\n{idx}. {article['title']}")
            print(f"   Published: {article['published_date']}")
            print(f"   URL: {article['url']}")
            print(f"   Preview: {article['content'][:400]}...")
