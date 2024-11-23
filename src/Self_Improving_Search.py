"""
Enhanced search functionality with multiple providers and self-improving capabilities.
"""
import time
import re
import os
from typing import List, Dict, Tuple, Union, Any
from colorama import Fore, Style
import logging
import sys
from io import StringIO
from .web_scraper import get_web_content, can_fetch
from .llm_config import get_llm_config
from .llm_response_parser import UltimateLLMResponseParser
from .llm_wrapper import LLMWrapper
from .search_manager import SearchManager
from urllib.parse import urlparse
from .system_config import RESEARCH_CONFIG

# Set up logging
log_directory = 'logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = os.path.join(log_directory, 'llama_output.log')
file_handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.handlers = []
logger.addHandler(file_handler)
logger.propagate = False

# Suppress other loggers
for name in ['root', 'duckduckgo_search', 'requests', 'urllib3']:
    logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger(name).handlers = []
    logging.getLogger(name).propagate = False

class OutputRedirector:
    def __init__(self, stream=None):
        self.stream = stream or StringIO()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def __enter__(self):
        sys.stdout = self.stream
        sys.stderr = self.stream
        return self.stream

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

class EnhancedSelfImprovingSearch:
    def __init__(self, llm: LLMWrapper, parser: UltimateLLMResponseParser, max_attempts: int = 5):
        self.llm = llm
        self.parser = parser
        self.max_attempts = max_attempts
        self.llm_config = get_llm_config()
        self.search_manager = SearchManager()
        
        # Rate limiting configuration
        self.requests_per_minute = RESEARCH_CONFIG['rate_limiting']['requests_per_minute']
        self.concurrent_requests = RESEARCH_CONFIG['rate_limiting']['concurrent_requests']
        self.cooldown_period = RESEARCH_CONFIG['rate_limiting']['cooldown_period']
        
        self.last_request_time = 0
        self.request_count = 0
        
        self.last_query = None
        self.last_time_range = None
        self.WHITESPACE_PATTERN = r'\s+'

    @staticmethod
    def initialize_llm():
        llm_wrapper = LLMWrapper()
        return llm_wrapper

    def print_thinking(self):
        print(Fore.MAGENTA + "🧠 Thinking..." + Style.RESET_ALL)

    def print_searching(self):
        print(Fore.MAGENTA + "📝 Searching..." + Style.RESET_ALL)

    def search_and_improve(self, user_query: str) -> str:
        attempt = 0
        while attempt < self.max_attempts:
            print(f"\n{Fore.CYAN}Search attempt {attempt + 1}:{Style.RESET_ALL}")
            self.print_searching()

            try:
                formulated_query, time_range = self.formulate_query(user_query, attempt)
                self.last_query = formulated_query
                self.last_time_range = time_range

                print(f"{Fore.YELLOW}Original query: {user_query}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Formulated query: {formulated_query}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Time range: {time_range}{Style.RESET_ALL}")

                if not formulated_query:
                    print(f"{Fore.RED}Error: Empty search query. Retrying...{Style.RESET_ALL}")
                    attempt += 1
                    continue

                search_results = self.perform_search(formulated_query, time_range)
                if not isinstance(search_results, dict):
                    print(f"{Fore.RED}Error: Invalid search results format. Expected dict, got {type(search_results)}{Style.RESET_ALL}")
                    attempt += 1
                    continue

                if not search_results.get('success') or not search_results.get('results'):
                    print(f"{Fore.RED}No results found. Retrying with a different query...{Style.RESET_ALL}")
                    attempt += 1
                    continue

                self.display_search_results(search_results)

                selected_urls = self.select_relevant_pages(search_results['results'], user_query)

                if not selected_urls:
                    print(f"{Fore.RED}No relevant URLs found. Retrying...{Style.RESET_ALL}")
                    attempt += 1
                    continue

                print(Fore.MAGENTA + "⚙️ Scraping selected pages..." + Style.RESET_ALL)
                scraped_content = self.scrape_content(selected_urls)

                if not scraped_content:
                    print(f"{Fore.RED}Failed to scrape content. Retrying...{Style.RESET_ALL}")
                    attempt += 1
                    continue

                self.display_scraped_content(scraped_content)

                self.print_thinking()

                with OutputRedirector() as output:
                    evaluation, decision = self.evaluate_scraped_content(user_query, scraped_content)
                llm_output = output.getvalue()
                logger.info(f"LLM Output in evaluate_scraped_content:\n{llm_output}")

                print(f"{Fore.MAGENTA}Evaluation: {evaluation}{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}Decision: {decision}{Style.RESET_ALL}")

                if decision == "answer":
                    # If Tavily provided an AI answer, include it in the final answer generation
                    ai_answer = search_results.get('answer', '') if search_results.get('provider') == 'tavily' else ''
                    return self.generate_final_answer(user_query, scraped_content, ai_answer)
                elif decision == "refine":
                    print(f"{Fore.YELLOW}Refining search...{Style.RESET_ALL}")
                    attempt += 1
                else:
                    print(f"{Fore.RED}Unexpected decision. Proceeding to answer.{Style.RESET_ALL}")
                    return self.generate_final_answer(user_query, scraped_content)

            except Exception as e:
                print(f"{Fore.RED}An error occurred during search attempt. Check the log file for details.{Style.RESET_ALL}")
                logger.error(f"An error occurred during search: {str(e)}", exc_info=True)
                attempt += 1

        return self.synthesize_final_answer(user_query)

    def formulate_query(self, query: str, attempt: int) -> Tuple[str, str]:
        """Placeholder for query formulation - returns original query and default time range."""
        return query, 'none'

    def perform_search(self, query: str, time_range: str) -> Dict[str, Any]:
        """
        Perform search using SearchManager with time range adaptation and rate limiting.
        """
        if not query:
            return {'success': False, 'error': 'Empty query', 'results': [], 'provider': None}
        
        # Rate limiting check
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        # Check if we need to cool down
        if self.request_count >= self.requests_per_minute:
            if time_since_last_request < self.cooldown_period:
                logger.warning(f"Rate limit reached. Cooling down for {self.cooldown_period - time_since_last_request:.1f} seconds")
                time.sleep(self.cooldown_period - time_since_last_request)
                self.request_count = 0
        
        # Update rate limiting trackers
        self.last_request_time = time.time()
        self.request_count += 1
        
        search_params = {
            'max_results': RESEARCH_CONFIG['search']['max_results_per_search'],
            'min_relevance_score': RESEARCH_CONFIG['search']['min_relevance_score']
        }
        
        # Add time range parameters if specified
        time_params = {
            'd': {'days': 1},
            'w': {'days': 7},
            'm': {'days': 30},
            'y': {'days': 365},
            'none': {}
        }
        search_params.update(time_params.get(time_range.lower(), {}))
        
        return self.search_manager.search(query, **search_params)

    def display_search_results(self, results: Dict[str, Any]) -> None:
        """Display search results with provider information"""
        try:
            if not results['success']:
                print(f"{Fore.RED}Search failed: {results.get('error', 'Unknown error')}{Style.RESET_ALL}")
                return

            print(f"\n{Fore.CYAN}Search Results from {results['provider'].upper()}:{Style.RESET_ALL}")
            print(f"Query: {self.last_query}")
            print(f"Time range: {self.last_time_range}")
            print(f"Number of results: {len(results['results'])}")
            
            if results.get('answer'):
                print(f"\n{Fore.GREEN}AI-Generated Summary:{Style.RESET_ALL}")
                print(results['answer'])

        except Exception as e:
            logger.error(f"Error displaying search results: {str(e)}")

    def select_relevant_pages(self, search_results: List[Dict], user_query: str) -> List[str]:
        prompt = (
            f"Given the following search results for the user's question: \"{user_query}\"\n"
            "Select the 2 most relevant results to scrape and analyze. Explain your reasoning for each selection.\n\n"
            f"Search Results:\n{self.format_results(search_results)}\n\n"
            "Instructions:\n"
            "1. You MUST select exactly 2 result numbers from the search results.\n"
            "2. Choose the results that are most likely to contain comprehensive and relevant information to answer the user's question.\n"
            "3. Provide a brief reason for each selection.\n\n"
            "You MUST respond using EXACTLY this format and nothing else:\n\n"
            "Selected Results: [Two numbers corresponding to the selected results]\n"
            "Reasoning: [Your reasoning for the selections]"
        )

        max_retries = 3
        for retry in range(max_retries):
            with OutputRedirector() as output:
                response_text = self.llm.generate(prompt, max_tokens=200, stop=None)
            llm_output = output.getvalue()
            logger.info(f"LLM Output in select_relevant_pages:\n{llm_output}")

            parsed_response = {int(char) for char in response_text[:40] if char.isdigit()}
            selected_urls = [search_results['results'][i-1]['url'] for i in parsed_response]

            allowed_urls = [url for url in selected_urls if can_fetch(url)]
            if allowed_urls:
                return allowed_urls
            else:
                print(f"{Fore.YELLOW}Warning: All selected URLs are disallowed by robots.txt. Retrying selection.{Style.RESET_ALL}")


        print(f"{Fore.YELLOW}Warning: All attempts to select relevant pages failed. Falling back to top allowed results.{Style.RESET_ALL}")
        allowed_urls = [result['url'] for result in search_results if can_fetch(result['url'])][:2]
        return allowed_urls


    def format_results(self, results: List[Dict]) -> str:
        formatted_results = []
        for i, result in enumerate(results['results'], 1):
            formatted_result = f"{i}. Title: {result.get('title', 'N/A')}\n"
            formatted_result += f"   Snippet: {result.get('content', 'N/A')[:200]}...\n"
            formatted_result += f"   URL: {result.get('url', 'N/A')}\n"
            if result.get('published_date'):
                formatted_result += f"   Published: {result['published_date']}\n"
            if result.get('score'):
                formatted_result += f"   Relevance Score: {result['score']}\n"
            formatted_results.append(formatted_result)
        return "\n".join(formatted_results)

    def scrape_content(self, urls: List[str]) -> Dict[str, str]:
        scraped_content = {}
        blocked_urls = []
        for url in urls:
            robots_allowed = can_fetch(url)
            if robots_allowed:
                content = get_web_content([url])
                if content:
                    scraped_content.update(content)
                    print(Fore.YELLOW + f"Successfully scraped: {url}" + Style.RESET_ALL)
                    logger.info(f"Successfully scraped: {url}")
                else:
                    print(Fore.RED + f"Robots.txt disallows scraping of {url}" + Style.RESET_ALL)
                    logger.warning(f"Robots.txt disallows scraping of {url}")
            else:
                blocked_urls.append(url)
                print(Fore.RED + f"Warning: Robots.txt disallows scraping of {url}" + Style.RESET_ALL)
                logger.warning(f"Robots.txt disallows scraping of {url}")

        print(Fore.CYAN + f"Scraped content received for {len(scraped_content)} URLs" + Style.RESET_ALL)
        logger.info(f"Scraped content received for {len(scraped_content)} URLs")

        if blocked_urls:
            print(Fore.RED + f"Warning: {len(blocked_urls)} URL(s) were not scraped due to robots.txt restrictions." + Style.RESET_ALL)
            logger.warning(f"{len(blocked_urls)} URL(s) were not scraped due to robots.txt restrictions: {', '.join(blocked_urls)}")

        return scraped_content

    def display_scraped_content(self, scraped_content: Dict[str, str]):
        print(f"\n{Fore.CYAN}Scraped Content:{Style.RESET_ALL}")
        for url, content in scraped_content.items():
            print(f"{Fore.GREEN}URL: {url}{Style.RESET_ALL}")
            print(f"Content: {content[:4000]}...\n")

    def generate_final_answer(self, user_query: str, scraped_content: Dict[str, str], ai_answer: str = '') -> str:
        user_query_short = user_query[:200]
        ai_summary = f"AI-Generated Summary:\n{ai_answer}\n\n" if ai_answer else ""
        
        prompt = (
            f"You are an AI assistant. Provide a comprehensive and detailed answer to the following question "
            f"using the provided information. Do not include any references or mention any sources. "
            f"Answer directly and thoroughly.\n\n"
            f"Question: \"{user_query_short}\"\n\n"
            f"{ai_summary}"
            f"Scraped Content:\n{self.format_scraped_content(scraped_content)}\n\n"
            f"Important Instructions:\n"
            f"1. Do not use phrases like \"Based on the absence of selected results\" or similar.\n"
            f"2. If the scraped content does not contain enough information to answer the question, "
            f"say so explicitly and explain what information is missing.\n"
            f"3. Provide as much relevant detail as possible from the scraped content.\n"
            f"4. If an AI-generated summary is provided, use it to enhance your answer but don't rely on it exclusively.\n\n"
            f"Answer:"
        )

        max_retries = 3
        for attempt in range(max_retries):
            with OutputRedirector() as output:
                response_text = self.llm.generate(prompt, max_tokens=4096, stop=None)
            llm_output = output.getvalue()
            logger.info(f"LLM Output in generate_final_answer:\n{llm_output}")
            if response_text:
                logger.info(f"LLM Response:\n{response_text}")
                return response_text

        error_message = "I apologize, but I couldn't generate a satisfactory answer based on the available information."
        logger.warning(f"Failed to generate a response after {max_retries} attempts. Returning error message.")
        return error_message

    def format_scraped_content(self, scraped_content: Dict[str, str]) -> str:
        formatted_content = []
        for url, content in scraped_content.items():
            content = re.sub(self.WHITESPACE_PATTERN, ' ', content)
            formatted_content.append(f"Content from {url}:{content}")
        return "\n".join(formatted_content)

    def synthesize_final_answer(self, user_query: str) -> str:
        prompt = (
            f"After multiple search attempts, we couldn't find a fully satisfactory answer to the user's question: "
            f"\"{user_query}\"\n\n"
            f"Please provide the best possible answer you can, acknowledging any limitations or uncertainties.\n"
            f"If appropriate, suggest ways the user might refine their question or where they might find more information.\n\n"
            f"Respond in a clear, concise, and informative manner."
        )
        try:
            with OutputRedirector() as output:
                response_text = self.llm.generate(prompt, max_tokens=self.llm_config.get('max_tokens', 1024), stop=self.llm_config.get('stop', None))
            llm_output = output.getvalue()
            logger.info(f"LLM Output in synthesize_final_answer:\n{llm_output}")
            if response_text:
                return response_text.strip()
        except Exception as e:
            logger.error(f"Error in synthesize_final_answer: {str(e)}", exc_info=True)
        return "I apologize, but after multiple attempts, I wasn't able to find a satisfactory answer to your question. Please try rephrasing your question or breaking it down into smaller, more specific queries."

# End of EnhancedSelfImprovingSearch class
