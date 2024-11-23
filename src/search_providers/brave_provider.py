from typing import Dict, Any, Optional
import os
import sys
from pathlib import Path
import requests
from datetime import datetime, timedelta
import json
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path for imports when running as script
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent))
    from search_providers.base_provider import BaseSearchProvider
else:
    from .base_provider import BaseSearchProvider

class BraveSearchProvider(BaseSearchProvider):
    """
    Brave implementation of the search provider interface.
    Handles both web and news-specific searches using Brave's APIs.
    """
    
    WEB_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
    NEWS_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/news/search"
    SUMMARIZER_ENDPOINT = "https://api.search.brave.com/res/v1/summarizer/search"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Brave search provider.
        
        Args:
            api_key: Optional Brave API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.pro_api_key = os.getenv("BRAVE_AI_PRO_API_KEY") #Optional, used for AI summary requests
        self.headers = {
            'X-Subscription-Token': self.api_key,
            'Accept': 'application/json'
        } if self.api_key else None
        self.proheaders = {
            'X-Subscription-Token': self.pro_api_key,
            'Accept': 'application/json'
        } if self.pro_api_key else None
    def is_configured(self) -> bool:
        """Check if Brave API is properly configured."""
        return self.headers is not None

    def get_brave_summary(self, query):
        # Query parameters
        params = {
            "q": query,
            "summary": 1
        }

        # Make the initial web search request to get summarizer key
        search_response = requests.get(self.WEB_SEARCH_ENDPOINT, headers=self.proheaders, params=params)

        if search_response.status_code == 200:
            data = search_response.json()

            if "summarizer" in data and "key" in data["summarizer"]:
                summarizer_key = data["summarizer"]["key"]

                # Make request to summarizer endpoint
                summarizer_params = {
                    "key": summarizer_key,
                    "entity_info": 1
                }

                summary_response = requests.get(
                    self.SUMMARIZER_ENDPOINT,
                    headers=self.proheaders,
                    params=summarizer_params
                )

                if summary_response.status_code == 200:
                    summary_data = summary_response.json()
                    try:
                        return summary_data['summary'][0]['data']
                    except (KeyError, IndexError):
                        return None

        return None
    
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Perform a search using Brave API.
        
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
            return {'error': 'Brave API key not configured'}

        try:
            # Set default search parameters
            search_params = {
                'count': str(kwargs.get('max_results', 10)),
                'country': kwargs.get('market', 'us'),  # Brave uses country code
                'q': query
            }
            
            # Determine if this is a news search
            if kwargs.get('topic') == 'news':
                # Add freshness parameter for news if days specified
                if 'days' in kwargs:
                    days = kwargs['days']
                    if days <= 1:
                        search_params['freshness'] = 'pd'  # past day
                    elif days <= 7:
                        search_params['freshness'] = 'pw'  # past week
                    else:
                        search_params['freshness'] = 'pm'  # past month

                response = requests.get(
                    self.NEWS_SEARCH_ENDPOINT,
                    headers=self.headers,
                    params=search_params
                )

                response_data = response.json()
                result = self._process_news_results(response_data, days=kwargs.get('days', 3), topic=query)
            else:
                response = requests.get(
                    self.WEB_SEARCH_ENDPOINT,
                    headers=self.headers,
                    params=search_params
                )
                response_data = response.json()
                result = self._process_general_results(response_data)

            # Include summarizer response if it exists
            summary_response = self.get_brave_summary(query)
            if summary_response:
                result['summarizer'] = summary_response
            
            return result
            
        except requests.exceptions.RequestException as e:
            return {'error': f'API request failed: {str(e)}'}
        except Exception as e:
            return {'error': f'An unexpected error occurred: {str(e)}'}
    
    def _process_general_results(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process results for general web searches."""
        web_results = response.get('web', {}).get('results', [])
        with ThreadPoolExecutor() as executor:
            # Use index as key instead of the result dictionary
            futures = {i: executor.submit(self.get_brave_summary, result.get('title', '')) 
                      for i, result in enumerate(web_results[:2])}
            
            results = []
            for i, result in enumerate(web_results):
                summary = None
                if i < 2:
                    try:
                        summary = futures[i].result()
                    except Exception as e:
                        print(f"Error getting summary: {e}")

                processed_result = {
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'content': result.get('description', ''),
                    'score': result.get('score', 1.0),
                    'extra_snippets': None,
                    'summary': None
                }
                if summary:
                    processed_result['summary'] = summary  
                else: 
                    processed_result['extra_snippets'] = result.get('extra_snippets', [])  
                results.append(processed_result)
        return {'results': results}
    
    def _process_news_results(self, response: Dict[str, Any], days: int, topic: str) -> Dict[str, Any]:
        """Process results for news-specific searches."""
        news_results = response.get('results', [])
        def convert_age_to_minutes(age_str: str) -> int:
            """
            Convert age string to minutes.
            
            Args:
                age_str: Age string in the format of "X minutes", "X hours", "X days"
            
            Returns:
                Age in minutes
            """
            age_value = int(age_str.split()[0])
            age_unit = age_str.split()[1]
            if age_unit == 'minutes':
                return age_value
            elif age_unit == 'hours':
                return age_value * 60
            elif age_unit == 'days':
                return age_value * 1440  # 24 hours * 60 minutes
            else:
                return 0  # Default to 0 if unknown unit

        # Sort news results based on the age field
        news_results.sort(key=lambda x: convert_age_to_minutes(x.get('age', '0 minutes')))
        
        with ThreadPoolExecutor() as executor:
            # Use enumerate to create futures with index as key
            futures = {i: executor.submit(self.get_brave_summary, article_data.get('title', '')) 
                      for i, article_data in enumerate(news_results)}
            
            articles = []
            for i, article_data in enumerate(news_results):
                try:
                    summary = futures[i].result()
                except Exception as e:
                    print(f"Error getting summary: {e}")
                    summary = None
                    
                article = {
                    'title': article_data.get('title', ''),
                    'url': article_data.get('url', ''),
                    'published_date': article_data.get('age', ''),
                    'breaking' : article_data.get('breaking', False),
                    'content': article_data.get('description', ''),
                    'extra_snippets': None,
                    'summary': None,
                    'score': article_data.get('score', 1.0)
                }
                if summary:
                    article['summary'] = summary
                else:
                    article['extra_snippets'] = article_data.get('extra_snippets', [])                   
                articles.append(article)

        return {
            'articles': articles,
            'time_period': f"Past {days} days",
            'topic': topic
        }

if __name__ == "__main__":
    # Test code using actual API
    provider = BraveSearchProvider()
    if not provider.is_configured():
        print("Error: Brave API key not configured")
        exit(1)

    # Test general search
    print("\n=== Testing General Search ===")
    general_result = provider.search(
        "What is artificial intelligence?",
        max_results=1 # Increased max_results to test summary limiting
    )
    
    if 'error' in general_result:
        print(f"Error in general search: {general_result['error']}")
    else:
        print("\nTop Results:")
        for idx, result in enumerate(general_result['results'], 1):
            print(f"\n{idx}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Preview: {result['content']}...")
            print(f"   Score: {result['score']}") 
            if result['extra_snippets']:
                print("   Extra Snippets:")
                for snippet in result['extra_snippets']:
                    print(f"   - {snippet}")
            if result['summary']:  # Check if summary exists before printing
                print(f"   Summary: {result.get('summary', '')}...")
    import time
    time.sleep(1)

    # Test news search
    print("\n\n=== Testing News Search ===")
    import time
    start_time = time.time()
    news_result = provider.search(
        "mike tyson fight",
        topic="news",
        days=3,
        max_results=1
    )
    end_time = time.time()

    
    if 'error' in news_result:
        print(f"Error in news search: {news_result['error']}")
    else:
        print("\nRecent Articles:")
        for idx, article in enumerate(news_result['articles'], 1):
            print(f"\n{idx}. {article['title']}")
            print(f"   Published: {article['published_date']}")
            print(f"   Breaking: {article['breaking']}")
            print(f"   URL: {article['url']}")
            print(f"   Preview: {article['content'][:400]}...")
            if article['extra_snippets']:
                print("   Extra Snippets:")
                for snippet in article['extra_snippets']:
                    print(f"     - {snippet}")
            if article['summary']:
                print(f"   Summary: {article.get('summary', '')}...")

    print(f"Execution time: {round(end_time - start_time, 1)} seconds")
