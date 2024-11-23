from typing import Dict, Any, Optional
import os
import sys
import json
from pathlib import Path
import requests
from datetime import datetime, timedelta

# Add parent directory to path for imports when running as script
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent))
    from search_providers.base_provider import BaseSearchProvider
else:
    from .base_provider import BaseSearchProvider

class ExaSearchProvider(BaseSearchProvider):
    """
    Exa.ai implementation of the search provider interface.
    Handles web searches with optional full page content retrieval.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Exa search provider.
        
        Args:
            api_key: Optional Exa API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("EXA_API_KEY")
        self.base_url = "https://api.exa.ai/search"
        self.trusted_sources = self._load_trusted_sources()
        
    def _load_trusted_sources(self) -> list:
        """Load trusted news sources from JSON file."""
        try:
            json_path = Path(__file__).parent / 'trusted_news_sources.json'
            with open(json_path) as f:
                data = json.load(f)
                return data.get('trusted_sources', [])
        except Exception as e:
            print(f"Warning: Could not load trusted sources: {e}")
            return []
        
    def is_configured(self) -> bool:
        """Check if Exa client is properly configured."""
        return bool(self.api_key)
    
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform a search using Exa API.
        
        Args:
            query: The search query string
            **kwargs: Additional search parameters:
                - include_content: Whether to retrieve full page contents (default: False)
                - max_results: Maximum number of results (default: 3)
                - days: Number of days to look back (for news searches)
                
        Returns:
            Dict containing search results or error information
        """
        if not self.is_configured():
            return {'error': 'Exa API key not configured'}

        try:
            # Set default search parameters
            search_params = {
                'query': query,
                'type': 'neural',
                'useAutoprompt': True,
                'numResults': kwargs.get('max_results', 3),
            }
            
            # Add optional parameters
            if kwargs.get('include_content'):
                search_params['contents'] = {
                    "highlights": True,
                    "summary": True
                }
                
            if kwargs.get('days'):
                # Convert days to timestamp for time-based filtering
                date_limit = datetime.now() - timedelta(days=kwargs['days'])
                search_params['startPublishedTime'] = date_limit.isoformat()
            
            # Add trusted domains for news searches
            if kwargs.get('topic') == 'news' and self.trusted_sources:
                search_params['includeDomains'] = self.trusted_sources

            # Make API request
            headers = {
                'x-api-key': self.api_key,
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=search_params
            )
            response.raise_for_status()
            data = response.json()
            
            # Process results based on whether it's a news search
            if kwargs.get('topic') == 'news':
                return self._process_news_results(
                    data,
                    days=kwargs.get('days', 3),
                    topic=query
                )
            else:
                return self._process_general_results(data)
            
        except requests.exceptions.RequestException as e:
            if e.response and e.response.status_code == 401:
                return {'error': 'Invalid Exa API key'}
            elif e.response and e.response.status_code == 429:
                return {'error': 'Exa API rate limit exceeded'}
            else:
                return {'error': f'An error occurred while making the request: {str(e)}'}
        except Exception as e:
            return {'error': f'An unexpected error occurred: {str(e)}'}
    
    def _process_general_results(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process results for general searches."""
        results = []
        for result in response.get('results', []):
            processed_result = {
                'title': result.get('title', ''),
                'url': result.get('url', ''),
                'highlights': result.get('highlights', []),
                'summary': result.get('summary', ''),
                'score': result.get('score', 0.0)
            }
            results.append(processed_result)
            
        return {
            'results': results,
            'autoprompt': response.get('autopromptString', '')
        }
    
    def _process_news_results(self, response: Dict[str, Any], days: int, topic: str) -> Dict[str, Any]:
        """Process results for news-specific searches."""
        articles = []
        for article in response.get('results', []):
                processed_article = {
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'published_date': article.get('publishedDate', ''),
                    'highlights': article.get('highlights', []),
                    'summary': article.get('summary', ''),
                    'score': article.get('score', 0.0)
                }
                articles.append(processed_article)
            
        return {
            'articles': articles,
            'time_period': f"Past {days} days",
            'topic': topic,
            'autoprompt': response.get('autopromptString', '')
        }

if __name__ == "__main__":
    # Test code for the Exa provider
    provider = ExaSearchProvider()
    if not provider.is_configured():
        print("Error: Exa API key not configured")
        exit(1)

    # Test general search
    print("\n=== Testing General Search ===")
    import time
    start_time = time.time()
    general_result = provider.search(
        "What is artificial intelligence?",
        max_results=3,
        include_content=True
    )
    end_time = time.time()
 
    if 'error' in general_result:
        print("Error:", general_result['error'])
    else:
        print("\nTop Results:")
        print(f"Autoprompt: {general_result.get('autoprompt', '')}")
        for idx, result in enumerate(general_result['results'], 1):
            print(f"\n{idx}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Score: {result['score']}")
            print(f"   Summary: {result['summary']}")
            if result['highlights']:
                print("   Highlights:")
                for highlight in result['highlights']:
                    print(f"   - {highlight}")
    print(f"\n\nTime taken for general search: {end_time - start_time} seconds")
  
    # Test news search
    print("\n\n=== Testing News Search ===")
    start_time = time.time()
    news_result = provider.search(
        "Latest developments in AI",
        topic="news",
        days=3,
        max_results=3,
        include_content=True
    )
    end_time = time.time()

    if 'error' in news_result:
        print("Error:", news_result['error'])
    else:
        print("\nRecent Articles:")
        print(f"Autoprompt: {news_result.get('autoprompt', '')}")
        for idx, article in enumerate(news_result['articles'], 1):
            print(f"\n{idx}. {article['title']}")
            print(f"   Published: {article['published_date']}")
            print(f"   URL: {article['url']}")
            print(f"   Score: {article['score']}")
            print(f"   Summary: {article['summary']}")
            if article['highlights']:
                print("   Highlights:")
                for highlight in article['highlights']:
                    print(f"   - {highlight}")
    print(f"\n\nTime taken for news search: {end_time - start_time} seconds")
    
    # Test error handling
    print("\n\n=== Testing Error Handling ===")
    bad_provider = ExaSearchProvider(api_key="invalid_key")
    error_result = bad_provider.search("test query")
    print("\nExpected error with invalid API key:", error_result['error'])
