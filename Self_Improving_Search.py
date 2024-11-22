import time
import re
import os
from typing import List, Dict, Tuple, Union
from colorama import Fore, Style
import logging
import sys
from io import StringIO
from web_scraper import get_web_content, can_fetch
from llm_config import get_llm_config
from llm_response_parser import UltimateLLMResponseParser
from llm_wrapper import LLMWrapper
from urllib.parse import urlparse
import duckduckgo_search

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
  """Windows-compatible output redirection"""
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
        self.last_query = ""  # Add this
        self.last_time_range = ""  # Add this

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

                print(f"{Fore.YELLOW}Original query: {user_query}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Formulated query: {formulated_query}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Time range: {time_range}{Style.RESET_ALL}")

                if not formulated_query:
                    print(f"{Fore.RED}Error: Empty search query. Retrying...{Style.RESET_ALL}")
                    attempt += 1
                    continue

                search_results = self.perform_search(formulated_query, time_range)

                if not search_results:
                    print(f"{Fore.RED}No results found. Retrying with a different query...{Style.RESET_ALL}")
                    attempt += 1
                    continue

                self.display_search_results(search_results)

                selected_urls = self.select_relevant_pages(search_results, user_query)

                if not selected_urls:
                    print(f"{Fore.RED}No relevant URLs found. Retrying...{Style.RESET_ALL}")
                    attempt += 1
                    continue

                print(Fore.MAGENTA + "⚙️ Scraping selected pages..." + Style.RESET_ALL)
                # Scraping is done without OutputRedirector to ensure messages are visible
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
                    return self.generate_final_answer(user_query, scraped_content)
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

    def evaluate_scraped_content(self, user_query: str, scraped_content: Dict[str, str]) -> Tuple[str, str]:
        user_query_short = user_query[:200]
        prompt = f"""
Evaluate if the following scraped content contains sufficient information to answer the user's question comprehensively:

User's question: "{user_query_short}"

Scraped Content:
{self.format_scraped_content(scraped_content)}

Your task:
1. Determine if the scraped content provides enough relevant and detailed information to answer the user's question thoroughly.
2. If the information is sufficient, decide to 'answer'. If more information or clarification is needed, decide to 'refine' the search.

Respond using EXACTLY this format:
Evaluation: [Your evaluation of the scraped content]
Decision: [ONLY 'answer' if content is sufficient, or 'refine' if more information is needed]
"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response_text = self.llm.generate(prompt, max_tokens=200, stop=None)
                evaluation, decision = self.parse_evaluation_response(response_text)
                if decision in ['answer', 'refine']:
                    return evaluation, decision
            except Exception as e:
                logger.warning(f"Error in evaluate_scraped_content (attempt {attempt + 1}): {str(e)}")

        logger.warning("Failed to get a valid decision in evaluate_scraped_content. Defaulting to 'refine'.")
        return "Failed to evaluate content.", "refine"

    def parse_evaluation_response(self, response: str) -> Tuple[str, str]:
        evaluation = ""
        decision = ""
        for line in response.strip().split('\n'):
            if line.startswith('Evaluation:'):
                evaluation = line.split(':', 1)[1].strip()
            elif line.startswith('Decision:'):
                decision = line.split(':', 1)[1].strip().lower()
        return evaluation, decision

    def formulate_query(self, user_query: str, attempt: int) -> Tuple[str, str]:
        user_query_short = user_query[:200]
        prompt = f"""
Based on the following user question, formulate a concise and effective search query:
"{user_query_short}"
Your task:
1. Create a search query of 2-5 words that will yield relevant results.
2. Determine if a specific time range is needed for the search.
Time range options:
- 'd': Limit results to the past day. Use for very recent events or rapidly changing information.
- 'w': Limit results to the past week. Use for recent events or topics with frequent updates.
- 'm': Limit results to the past month. Use for relatively recent information or ongoing events.
- 'y': Limit results to the past year. Use for annual events or information that changes yearly.
- 'none': No time limit. Use for historical information or topics not tied to a specific time frame.
Respond in the following format:
Search query: [Your 2-5 word query]
Time range: [d/w/m/y/none]
Do not provide any additional information or explanation.
"""
        max_retries = 3
        for retry in range(max_retries):
            with OutputRedirector() as output:
                response_text = self.llm.generate(prompt, max_tokens=50, stop=None)
            llm_output = output.getvalue()
            logger.info(f"LLM Output in formulate_query:\n{llm_output}")
            query, time_range = self.parse_query_response(response_text)
            if query and time_range:
                return query, time_range
        return self.fallback_query(user_query), "none"

    def parse_query_response(self, response: str) -> Tuple[str, str]:
        query = ""
        time_range = "none"
        for line in response.strip().split('\n'):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if "query" in key:
                    query = self.clean_query(value)
                elif "time" in key or "range" in key:
                    time_range = self.validate_time_range(value)
        return query, time_range

    def clean_query(self, query: str) -> str:
        query = re.sub(r'["\'\[\]]', '', query)
        query = re.sub(r'\s+', ' ', query)
        return query.strip()[:100]

    def validate_time_range(self, time_range: str) -> str:
        valid_ranges = ['d', 'w', 'm', 'y', 'none']
        time_range = time_range.lower()
        return time_range if time_range in valid_ranges else 'none'

    def fallback_query(self, user_query: str) -> str:
        words = user_query.split()
        return " ".join(words[:5])

    def perform_search(self, query: str, time_range: str) -> List[Dict]:
        """Performs the actual web search with enhanced error handling"""
        if not query:
            return []

        from duckduckgo_search import DDGS

        # Store the last query and time range for display purposes
        self.last_query = query
        self.last_time_range = time_range

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with DDGS() as ddgs:
                    try:
                        if time_range and time_range != 'none':
                            results = list(ddgs.text(
                                query, 
                                timelimit=time_range, 
                                max_results=10,
                                backend='api'  # Use API backend for more reliable results
                            ))
                        else:
                            results = list(ddgs.text(
                                query, 
                                max_results=10,
                                backend='api'  # Use API backend for more reliable results
                            ))

                        if results:
                            return [{'number': i+1, **result} for i, result in enumerate(results)]
                        else:
                            print(f"{Fore.YELLOW}No results found on attempt {attempt + 1}. Retrying...{Style.RESET_ALL}")
                            time.sleep(1)  # Add delay between retries
                            
                    except Exception as e:
                        logger.error(f"DuckDuckGo search error on attempt {attempt + 1}: {str(e)}")
                        print(f"{Fore.RED}Search error on attempt {attempt + 1}: {str(e)}{Style.RESET_ALL}")
                        time.sleep(1)  # Add delay between retries
                        continue

            except Exception as e:
                logger.error(f"DDGS initialization error on attempt {attempt + 1}: {str(e)}")
                print(f"{Fore.RED}Search initialization error on attempt {attempt + 1}: {str(e)}{Style.RESET_ALL}")
                time.sleep(1)  # Add delay between retries
                continue

        print(f"{Fore.RED}Search failed after {max_retries} attempts{Style.RESET_ALL}")
        return []

    def display_search_results(self, results: List[Dict]) -> None:
        """Display search results with minimal output"""
        try:
            if not results:
                return

            # Only show search success status
            print(f"\nSearch query sent to DuckDuckGo: {self.last_query}")
            print(f"Time range sent to DuckDuckGo: {self.last_time_range}")
            print(f"Number of results: {len(results)}")

        except Exception as e:
            logger.error(f"Error displaying search results: {str(e)}")

    def select_relevant_pages(self, search_results: List[Dict], user_query: str) -> List[str]:
        prompt = f"""
Given the following search results for the user's question: "{user_query}"
Select the 2 most relevant results to scrape and analyze. Explain your reasoning for each selection.

Search Results:
{self.format_results(search_results)}

Instructions:
1. You MUST select exactly 2 result numbers from the search results.
2. Choose the results that are most likely to contain comprehensive and relevant information to answer the user's question.
3. Provide a brief reason for each selection.

You MUST respond using EXACTLY this format and nothing else:

Selected Results: [Two numbers corresponding to the selected results]
Reasoning: [Your reasoning for the selections]
"""

        max_retries = 3
        for retry in range(max_retries):
            with OutputRedirector() as output:
                response_text = self.llm.generate(prompt, max_tokens=200, stop=None)
            llm_output = output.getvalue()
            logger.info(f"LLM Output in select_relevant_pages:\n{llm_output}")

            parsed_response = self.parse_page_selection_response(response_text)
            if parsed_response and self.validate_page_selection_response(parsed_response, len(search_results)):
                selected_urls = [result['href'] for result in search_results if result['number'] in parsed_response['selected_results']]

                allowed_urls = [url for url in selected_urls if can_fetch(url)]
                if allowed_urls:
                    return allowed_urls
                else:
                    print(f"{Fore.YELLOW}Warning: All selected URLs are disallowed by robots.txt. Retrying selection.{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Warning: Invalid page selection. Retrying.{Style.RESET_ALL}")

        print(f"{Fore.YELLOW}Warning: All attempts to select relevant pages failed. Falling back to top allowed results.{Style.RESET_ALL}")
        allowed_urls = [result['href'] for result in search_results if can_fetch(result['href'])][:2]
        return allowed_urls

    def parse_page_selection_response(self, response: str) -> Dict[str, Union[List[int], str]]:
        lines = response.strip().split('\n')
        parsed = {}
        for line in lines:
            if line.startswith('Selected Results:'):
                parsed['selected_results'] = [int(num.strip()) for num in re.findall(r'\d+', line)]
            elif line.startswith('Reasoning:'):
                parsed['reasoning'] = line.split(':', 1)[1].strip()
        return parsed if 'selected_results' in parsed and 'reasoning' in parsed else None

    def validate_page_selection_response(self, parsed_response: Dict[str, Union[List[int], str]], num_results: int) -> bool:
        if len(parsed_response['selected_results']) != 2:
            return False
        if any(num < 1 or num > num_results for num in parsed_response['selected_results']):
            return False
        return True

    def format_results(self, results: List[Dict]) -> str:
        formatted_results = []
        for result in results:
            formatted_result = f"{result['number']}. Title: {result.get('title', 'N/A')}\n"
            formatted_result += f"   Snippet: {result.get('body', 'N/A')[:200]}...\n"
            formatted_result += f"   URL: {result.get('href', 'N/A')}\n"
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

    def generate_final_answer(self, user_query: str, scraped_content: Dict[str, str]) -> str:
        user_query_short = user_query[:200]
        prompt = f"""
You are an AI assistant. Provide a comprehensive and detailed answer to the following question using ONLY the information provided in the scraped content. Do not include any references or mention any sources. Answer directly and thoroughly.

Question: "{user_query_short}"

Scraped Content:
{self.format_scraped_content(scraped_content)}

Important Instructions:
1. Do not use phrases like "Based on the absence of selected results" or similar.
2. If the scraped content does not contain enough information to answer the question, say so explicitly and explain what information is missing.
3. Provide as much relevant detail as possible from the scraped content.

Answer:
"""
        max_retries = 3
        for attempt in range(max_retries):
            with OutputRedirector() as output:
                response_text = self.llm.generate(prompt, max_tokens=1024, stop=None)
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
            content = re.sub(r'\s+', ' ', content)
            formatted_content.append(f"Content from {url}:\n{content}\n")
        return "\n".join(formatted_content)

    def synthesize_final_answer(self, user_query: str) -> str:
        prompt = f"""
After multiple search attempts, we couldn't find a fully satisfactory answer to the user's question: "{user_query}"

Please provide the best possible answer you can, acknowledging any limitations or uncertainties.
If appropriate, suggest ways the user might refine their question or where they might find more information.

Respond in a clear, concise, and informative manner.
"""
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
