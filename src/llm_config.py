# llm_config.py

LLM_TYPE = "openai"  # Options: 'llama_cpp', 'ollama', 'openai', 'anthropic'

# LLM settings for llama_cpp
MODEL_PATH = "/home/james/llama.cpp/models/gemma-2-9b-it-Q6_K.gguf" # Replace with your llama.cpp models filepath

LLM_CONFIG_LLAMA_CPP = {
    "llm_type": "llama_cpp",
    "model_path": MODEL_PATH,
    "n_ctx": 20000,  # context size
    "n_gpu_layers": 0,  # number of layers to offload to GPU (-1 for all, 0 for none)
    "n_threads": 8,  # number of threads to use
    "temperature": 0.7,  # temperature for sampling
    "top_p": 0.9,  # top p for sampling
    "top_k": 40,  # top k for sampling
    "repeat_penalty": 1.1,  # repeat penalty
    "max_tokens": 1024,  # max tokens to generate
    "stop": ["User:", "\n\n"]  # stop sequences
}

# LLM settings for Ollama
LLM_CONFIG_OLLAMA = {
    "llm_type": "ollama",
    "base_url": "http://localhost:11434",  # default Ollama server URL
    "model_name": "custom-phi3-32k-Q4_K_M",  # Replace with your Ollama model name
    "temperature": 0.7,
    "top_p": 0.9,
    "n_ctx": 55000,
    "context_length": 55000,
    "stop": ["User:", "\n\n"]
}

# LLM settings for OpenAI
LLM_CONFIG_OPENAI = {
    "llm_type": "openai",
    "api_key": "",  # Set via environment variable OPENAI_API_KEY
    "base_url": None,  # Optional: Set to use alternative OpenAI-compatible endpoints
    "model_name": "gpt-4o",  # Required: Specify the model to use
    "messages": [],  # Placeholder for conversation history
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 32000,
    "stop": ["User:", "\n\n"],
    "presence_penalty": 0,
    "frequency_penalty": 0
}

# LLM settings for Anthropic
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
