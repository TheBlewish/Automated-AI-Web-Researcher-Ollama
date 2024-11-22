# llm_config.py

LLM_TYPE = "openai"  # Options: 'llama_cpp', 'ollama', 'openai'

# LLM settings for llama_cpp
MODEL_PATH = "/home/james/llama.cpp/models/gemma-2-9b-it-Q6_K.gguf"

LLM_CONFIG_LLAMA_CPP = {
    "llm_type": "llama_cpp",
    "model_path": MODEL_PATH,
    "n_ctx": 20000,
    "n_gpu_layers": 0,
    "n_threads": 8,
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "max_tokens": 1024,
    "stop": ["User:", "\n\n"]
}

# LLM settings for Ollama
LLM_CONFIG_OLLAMA = {
    "base_url": "https://api.openai.com/v1",
    "llm_type": "ollama",
    "base_url": "http://localhost:11434",
    "model_name": "custom-phi3-32k-Q4_K_M",
    "temperature": 0.7,
    "top_p": 0.9,
    "n_ctx": 55000,
    "context_length": 55000,
    "stop": ["User:", "\n\n"]
}

# New: LLM settings for OpenAI
LLM_CONFIG_OPENAI = {
    "llm_type": "openai",
    "model_name": "gpt-4o-mini",  
    "api_key": "",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 4096,
    "stop": ["User:", "\n\n"],
    "context_length": 128000  # GPT-4 Turbo context window
}

def get_llm_config():
    if LLM_TYPE == "llama_cpp":
        return LLM_CONFIG_LLAMA_CPP
    elif LLM_TYPE == "ollama":
        return LLM_CONFIG_OLLAMA
    elif LLM_TYPE == "openai":
        return LLM_CONFIG_OPENAI
    else:
        raise ValueError(f"Invalid LLM_TYPE: {LLM_TYPE}")
