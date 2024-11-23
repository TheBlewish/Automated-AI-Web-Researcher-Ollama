"""
System-wide configuration settings for Web Scraper, Logging, and Research components
"""
import logging
import logging.handlers

# Web Scraper Configuration
SCRAPER_CONFIG = {
    "user_agent": "WebLLMAssistant/1.0 (+https://github.com/YourUsername/Web-LLM-Assistant-Llama-cpp)",
    "rate_limit": 1,  # Seconds between requests to same domain
    "timeout": 10,    # Request timeout in seconds
    "max_retries": 3, # Number of retry attempts for failed requests
    "max_workers": 5, # Maximum number of concurrent scraping threads
    "content_limits": {
        "max_content_length": 2400,  # Maximum characters to extract from content
        "max_links": 10             # Maximum number of links to extract
    },
    "respect_robots_txt": False     # Whether to respect robots.txt
}

# Search Provider Configuration
SEARCH_CONFIG = {
    "default_provider": "duckduckgo",  # Default search provider to use
    "fallback_order": [           # Order of providers to try if default fails
        "exa",
        "bing",
        "brave",
        "tavily",
        "duckduckgo"             # Keep DuckDuckGo as final fallback
    ],
    "provider_settings": {
        "tavily": {
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": True,
            "include_images": False
        },
        "brave": {
            "max_results": 10
        },
        "bing": {
            "max_results": 10,
            "freshness": "Month"  # Time range for results
        },
        "exa": {
            "max_results": 10,
            "use_highlights": True
        },
        "duckduckgo": {
            "max_results": 10,
            "region": "wt-wt",    # Worldwide results
            "safesearch": "off"
        }
    },
    "rate_limiting": {
        "requests_per_minute": 10,
        "cooldown_period": 60     # Seconds to wait after hitting rate limit
    }
}

# System-wide Logging Configuration
LOGGING_CONFIG = {
    "level": logging.INFO,
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "handlers": {
        "console": {
            "enabled": True,
            "level": logging.INFO
        },
        "file": {
            "enabled": True,
            "level": logging.DEBUG,
            "filename": "web_llm.log",
            "max_bytes": 1024 * 1024,  # 1MB
            "backup_count": 3
        }
    }
}

# Research Configuration
RESEARCH_CONFIG = {
    "search": {
        "max_searches_per_cycle": 5,
        "max_results_per_search": 10,
        "min_relevance_score": 0.6
    },
    "content": {
        "max_document_size": 12000,  # Maximum size of research document in characters
        "max_chunk_size": 2000,       # Maximum size of content chunks for processing
        "min_chunk_size": 100         # Minimum size of content chunks to process
    },
    "storage": {
        "auto_save": True,
        "auto_save_interval": 150,     # Auto-save interval in seconds
        "backup_enabled": True,
        "max_backups": 2
    },
    "rate_limiting": {
        "requests_per_minute": 60,
        "concurrent_requests": 5,
        "cooldown_period": 60         # Seconds to wait after hitting rate limit
    }
}

def setup_logging():
    """Configure logging based on LOGGING_CONFIG settings"""
    logging.basicConfig(
        level=LOGGING_CONFIG["level"],
        format=LOGGING_CONFIG["format"]
    )

    logger = logging.getLogger()
    
    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    if LOGGING_CONFIG["handlers"]["console"]["enabled"]:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOGGING_CONFIG["handlers"]["console"]["level"])
        console_handler.setFormatter(logging.Formatter(LOGGING_CONFIG["format"]))
        logger.addHandler(console_handler)

    # File handler
    if LOGGING_CONFIG["handlers"]["file"]["enabled"]:
        file_handler = logging.handlers.RotatingFileHandler(
            LOGGING_CONFIG["handlers"]["file"]["filename"],
            maxBytes=LOGGING_CONFIG["handlers"]["file"]["max_bytes"],
            backupCount=LOGGING_CONFIG["handlers"]["file"]["backup_count"]
        )
        file_handler.setLevel(LOGGING_CONFIG["handlers"]["file"]["level"])
        file_handler.setFormatter(logging.Formatter(LOGGING_CONFIG["format"]))
        logger.addHandler(file_handler)

    return logger

def get_scraper_config():
    """Get the web scraper configuration"""
    return SCRAPER_CONFIG

def get_research_config():
    """Get the research configuration"""
    return RESEARCH_CONFIG

def get_search_config():
    """Get the search provider configuration"""
    return SEARCH_CONFIG
