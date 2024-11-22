# llm_config.py

LLM_TYPE = "ollama"  # Options: 'llama_cpp', 'ollama'

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
    # change base_url to http://host.docker.internal:11434 in devcontainer
    "base_url": "http://localhost:11434",  # default Ollama server URL
    "model_name": "custom-phi3-32k-Q4_K_M",  # Replace with your Ollama model name
    "temperature": 0.7,
    "top_p": 0.9,
    "n_ctx": 55000,
    "context_length": 55000,
    "stop": ["User:", "\n\n"]
}

def get_llm_config():
    if LLM_TYPE == "llama_cpp":
        return LLM_CONFIG_LLAMA_CPP
    elif LLM_TYPE == "ollama":
        return LLM_CONFIG_OLLAMA
    else:
        raise ValueError(f"Invalid LLM_TYPE: {LLM_TYPE}")
