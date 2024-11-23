import requests
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, urljoin
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, user_agent="WebLLMAssistant/1.0 (+https://github.com/YourUsername/Web-LLM-Assistant-Llama-cpp)",
                 rate_limit=1, timeout=10, max_retries=3):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.robot_parser = RobotFileParser()
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_request_time = {}

    def can_fetch(self, url):
        # parsed_url = urlparse(url)
        # robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        # self.robot_parser.set_url(robots_url)
        # try:
        #     self.robot_parser.read()
        #     return self.robot_parser.can_fetch(self.session.headers["User-Agent"], url)
        # except Exception as e:
        #     logger.warning(f"Error reading robots.txt for {url}: {e}")
            return True  # ignore robots.txt

    def respect_rate_limit(self, url):
        domain = urlparse(url).netloc
        current_time = time.time()
        if domain in self.last_request_time:
            time_since_last_request = current_time - self.last_request_time[domain]
            if time_since_last_request < self.rate_limit:
                time.sleep(self.rate_limit - time_since_last_request)
        self.last_request_time[domain] = time.time()

    def scrape_page(self, url):
        if not self.can_fetch(url):
            logger.info(f"Robots.txt disallows scraping: {url}")
            return None

        for attempt in range(self.max_retries):
            try:
                self.respect_rate_limit(url)
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return self.extract_content(response.text, url)
            except requests.RequestException as e:
                logger.warning(f"Error scraping {url} (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed to scrape {url} after {self.max_retries} attempts")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff

    def extract_content(self, html, url):
        soup = BeautifulSoup(html, 'html.parser')

        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Extract title
        title = soup.title.string if soup.title else ""

        # Try to find main content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')

        if main_content:
            paragraphs = main_content.find_all('p')
        else:
            paragraphs = soup.find_all('p')

        # Extract text from paragraphs
        text = ' '.join([p.get_text().strip() for p in paragraphs])

        # If no paragraphs found, get all text
        if not text:
            text = soup.get_text()

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Extract and resolve links
        links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]

        return {
            "url": url,
            "title": title,
            "content": text[:2400],  # Limit to first 2400 characters
            "links": links[:10]  # Limit to first 10 links
        }

def scrape_multiple_pages(urls, max_workers=5):
    scraper = WebScraper()
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(scraper.scrape_page, url): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                if data:
                    results[url] = data
                    logger.info(f"Successfully scraped: {url}")
                else:
                    logger.warning(f"Failed to scrape: {url}")
            except Exception as exc:
                logger.error(f"{url} generated an exception: {exc}")

    return results

# Function to integrate with your main system
def get_web_content(urls):
    scraped_data = scrape_multiple_pages(urls)
    return {url: data['content'] for url, data in scraped_data.items() if data}

# Standalone can_fetch function
def can_fetch(url):
    # parsed_url = urlparse(url)
    # robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    # rp = RobotFileParser()
    # rp.set_url(robots_url)
    # try:
    #     rp.read()
    #     return rp.can_fetch("*", url)
    # except Exception as e:
    #     logger.warning(f"Error reading robots.txt for {url}: {e}")
        return True  # ignore robots.xt

if __name__ == "__main__":
    test_urls = [
        "https://en.wikipedia.org/wiki/Web_scraping",
        "https://example.com",
        "https://www.python.org"
    ]
    scraped_content = get_web_content(test_urls)
    for url, content in scraped_content.items():
        print(f"Content from {url}:")
        print(content[:500])  # Print first 500 characters
        print("\n---\n")
