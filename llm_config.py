# llm_config.py

LLM_TYPE = "ollama"  # Options: 'ollama', 'openai', 'anthropic'

# LLM settings for Ollama
LLM_CONFIG_OLLAMA = {
    "llm_type": "ollama",
    "base_url": "http://localhost:11434",  # default Ollama server URL
    "model_name": "custom-phi3-32k-Q4_K_M",  # Replace with your Ollama model name
    "temperature": 0.7,
    "top_p": 0.9,
    "n_ctx": 55000,
    "stop": ["User:", "\n\n"]
}

# LLM settings for OpenAI 
# WARNING: This application makes frequent API calls during research operations. If using paid API services 
# (OpenAI/Anthropic), this can result in significant costs accumulating quickly - proceed with caution and 
# monitor your API usage carefully if it's paid.
LLM_CONFIG_OPENAI = {
    "llm_type": "openai",
    "api_key": "",  # Set via environment variable OPENAI_API_KEY
    "base_url": None,  # Optional: Set to use alternative OpenAI-compatible endpoints
    "model_name": "gpt-4o",  # Required: Specify the model to use
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 4096,
    "stop": ["User:", "\n\n"],
    "presence_penalty": 0,
    "frequency_penalty": 0
}

# LLM settings for Anthropic
# WARNING: This application makes frequent API calls during research operations. If using paid API services 
# (OpenAI/Anthropic), this can result in significant costs accumulating quickly - proceed with caution and 
# monitor your API usage carefully if it's paid.
LLM_CONFIG_ANTHROPIC = {
    "llm_type": "anthropic",
    "api_key": "",  # Set via environment variable ANTHROPIC_API_KEY
    "model_name": "claude-3-5-sonnet-latest",  # Required: Specify the model to use
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 4096,
    "stop": ["User:", "\n\n"]
}

def get_llm_config():
    if LLM_TYPE == "llama_cpp":
        return LLM_CONFIG_LLAMA_CPP
    elif LLM_TYPE == "ollama":
        return LLM_CONFIG_OLLAMA
    elif LLM_TYPE == "openai":
        return LLM_CONFIG_OPENAI
    elif LLM_TYPE == "anthropic":
        return LLM_CONFIG_ANTHROPIC
    else:
        raise ValueError(f"Invalid LLM_TYPE: {LLM_TYPE}")
