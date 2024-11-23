from typing import Dict, Any, Optional
import os
import sys
from pathlib import Path

# Add parent directory to path for imports when running as script
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent))
    from search_providers.base_provider import BaseSearchProvider
else:
    from .base_provider import BaseSearchProvider

from tavily import TavilyClient, MissingAPIKeyError, InvalidAPIKeyError, UsageLimitExceededError

class TavilySearchProvider(BaseSearchProvider):
    """
    Tavily implementation of the search provider interface.
    Handles both general and news-specific searches.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Tavily search provider.
        
        Args:
            api_key: Optional Tavily API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        try:
            self.client = TavilyClient(api_key=self.api_key) if self.api_key else None
        except MissingAPIKeyError:
            self.client = None
    
    def is_configured(self) -> bool:
        """Check if Tavily client is properly configured."""
        return self.client is not None
    
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform a search using Tavily API.
        
        Args:
            query: The search query string
            **kwargs: Additional search parameters:
                - search_depth: "basic" or "advanced" (default: "basic")
                - topic: Optional search topic (e.g., "news")
                - max_results: Maximum number of results (default: 5)
                - include_answer: Whether to include AI-generated answer (default: True)
                - include_images: Whether to include images (default: False)
                - days: Number of days to look back (for news searches)
                
        Returns:
            Dict containing search results or error information
        """
        if not self.is_configured():
            return {'error': 'Tavily API key not configured'}

        try:
            # Set default search parameters
            search_params = {
                'search_depth': "basic",
                'max_results': 5,
                'include_answer': True,
                'include_images': False
            }
            
            # Update with any provided parameters
            search_params.update(kwargs)
            
            # Execute search
            response = self.client.search(query, **search_params)
            
            # Process results based on whether it's a news search
            if kwargs.get('topic') == 'news':
                return self._process_news_results(
                    response,
                    days=kwargs.get('days', 3),
                    topic=query
                )
            else:
                return self._process_general_results(response)
            
        except InvalidAPIKeyError:
            return {'error': 'Invalid Tavily API key'}
        except UsageLimitExceededError:
            return {'error': 'Tavily API usage limit exceeded'}
        except Exception as e:
            return {'error': f'An unexpected error occurred: {e}'}
    
    def _process_general_results(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process results for general searches."""
        return {
            'answer': response.get('answer', ''),
            'results': [{
                'title': result.get('title', ''),
                'url': result.get('url', ''),
                'content': result.get('content', '')[:500] + '...' if result.get('content') else '',
                'score': result.get('score', 0.0)
            } for result in response.get('results', [])]
        }
    
    def _process_news_results(self, response: Dict[str, Any], days: int, topic: str) -> Dict[str, Any]:
        """Process results for news-specific searches."""
        return {
            'answer': response.get('answer', ''),
            'articles': [{
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'published_date': article.get('published_date', ''),
                'content': article.get('content', '')[:500] + '...' if article.get('content') else '',
                'score': article.get('score', 0.0)
            } for article in response.get('results', [])],
            'time_period': f"Past {days} days",
            'topic': topic
        }

if __name__ == "__main__":
    # Test code for the Tavily provider
    provider = TavilySearchProvider()
    if not provider.is_configured():
        print("Error: Tavily API key not configured")
        exit(1)

    # Test general search
    print("\n=== Testing General Search ===")
    general_result = provider.search(
        "What is artificial intelligence?",
        search_depth="advanced",
        max_results=3
    )
    print("\nQuery Answer:", general_result['answer'])
    print("\nTop Results:")
    for idx, result in enumerate(general_result['results'], 1):
        print(f"\n{idx}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Score: {result['score']}")
        print(f"   Preview: {result['content'][:200]}...")

    # Test news search
    print("\n\n=== Testing News Search ===")
    news_result = provider.search(
        "Latest developments in AI",
        topic="news",
        days=3,
        search_depth="advanced"
    )
    print("\nNews Summary:", news_result['answer'])
    print("\nRecent Articles:")
    for idx, article in enumerate(news_result['articles'], 1):
        print(f"\n{idx}. {article['title']}")
        print(f"   Published: {article['published_date']}")
        print(f"   URL: {article['url']}")
        print(f"   Score: {article['score']}")
        print(f"   Preview: {article['content'][:400]}...")

    # Test error handling
    print("\n\n=== Testing Error Handling ===")
    bad_provider = TavilySearchProvider(api_key="invalid_key")
    error_result = bad_provider.search("test query")
    print("\nExpected error with invalid API key:", error_result['error'])
