import os
from llama_cpp import Llama
import requests
import json
from .llm_config import get_llm_config
from openai import OpenAI
from anthropic import Anthropic

class LLMWrapper:
    def __init__(self):
        self.llm_config = get_llm_config()
        self.llm_type = self.llm_config.get('llm_type', 'llama_cpp')
        
        if self.llm_type == 'llama_cpp':
            self.llm = self._initialize_llama_cpp()
        elif self.llm_type == 'ollama':
            self.base_url = self.llm_config.get('base_url', 'http://localhost:11434')
            self.model_name = self.llm_config.get('model_name', 'your_model_name')
        elif self.llm_type == 'openai':
            self._initialize_openai()
        elif self.llm_type == 'anthropic':
            self._initialize_anthropic()
        else:
            raise ValueError(f"Unsupported LLM type: {self.llm_type}")

    def _initialize_llama_cpp(self):
        return Llama(
            model_path=self.llm_config.get('model_path'),
            n_ctx=self.llm_config.get('n_ctx', 55000),
            n_gpu_layers=self.llm_config.get('n_gpu_layers', 0),
            n_threads=self.llm_config.get('n_threads', 8),
            verbose=False
        )

    def _initialize_openai(self):
        api_key = os.getenv('OPENAI_API_KEY') or self.llm_config.get('api_key')
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        base_url = self.llm_config.get('base_url')
        model_name = self.llm_config.get('model_name')
        
        if not model_name:
            raise ValueError("OpenAI model name not specified in config")
            
        client_kwargs = {'api_key': api_key}
        if base_url:
            client_kwargs['base_url'] = base_url
            
        self.client = OpenAI(**client_kwargs)
        self.model_name = model_name

    def _initialize_anthropic(self):
        api_key = os.getenv('ANTHROPIC_API_KEY') or self.llm_config.get('api_key')
        if not api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
            
        model_name = self.llm_config.get('model_name')
        if not model_name:
            raise ValueError("Anthropic model name not specified in config")
            
        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name

    def generate(self, prompt, **kwargs):
        if self.llm_type == 'llama_cpp':
            llama_kwargs = self._prepare_llama_kwargs(kwargs)
            response = self.llm(prompt, **llama_kwargs)
            return response['choices'][0]['text'].strip()
        elif self.llm_type == 'ollama':
            return self._ollama_generate(prompt, **kwargs)
        elif self.llm_type == 'openai':
            return self._openai_generate(prompt, **kwargs)
        elif self.llm_type == 'anthropic':
            return self._anthropic_generate(prompt, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM type: {self.llm_type}")

    def _ollama_generate(self, prompt, **kwargs):
        url = f"{self.base_url}/api/generate"
        data = {
            'model': self.model_name,
            'prompt': prompt,
            'options': {
                'temperature': kwargs.get('temperature', self.llm_config.get('temperature', 0.7)),
                'top_p': kwargs.get('top_p', self.llm_config.get('top_p', 0.9)),
                'stop': kwargs.get('stop', self.llm_config.get('stop', [])),
                'num_predict': kwargs.get('max_tokens', self.llm_config.get('max_tokens', 55000)),
                'num_ctx': self.llm_config.get('n_ctx', 55000)
            }
        }
        response = requests.post(url, json=data, stream=True)
        if response.status_code != 200:
            raise Exception(f"Ollama API request failed with status {response.status_code}: {response.text}")
        text = ''.join(json.loads(line)['response'] for line in response.iter_lines() if line)
        return text.strip()

    def _openai_generate(self, prompt, **kwargs):
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get('temperature', self.llm_config.get('temperature', 0.7)),
                top_p=kwargs.get('top_p', self.llm_config.get('top_p', 0.9)),
                max_tokens=kwargs.get('max_tokens', self.llm_config.get('max_tokens', 4096)),
                stop=kwargs.get('stop', self.llm_config.get('stop', [])),
                presence_penalty=self.llm_config.get('presence_penalty', 0),
                frequency_penalty=self.llm_config.get('frequency_penalty', 0)
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")

    def _anthropic_generate(self, prompt, **kwargs):
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=kwargs.get('max_tokens', self.llm_config.get('max_tokens', 4096)),
                temperature=kwargs.get('temperature', self.llm_config.get('temperature', 0.7)),
                top_p=kwargs.get('top_p', self.llm_config.get('top_p', 0.9)),
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            return response.content[0].text.strip()
        except Exception as e:
            raise Exception(f"Anthropic API request failed: {str(e)}")

    def _cleanup(self):
        """Force terminate any running LLM processes"""
        if self.llm_type == 'ollama':
            try:
                # Force terminate Ollama process
                requests.post(f"{self.base_url}/api/terminate")
            except:
                pass

            try:
                # Also try to terminate via subprocess if needed
                import subprocess
                subprocess.run(['pkill', '-f', 'ollama'], capture_output=True)
            except:
                pass

    def _prepare_llama_kwargs(self, kwargs):
        llama_kwargs = {
            'max_tokens': kwargs.get('max_tokens', self.llm_config.get('max_tokens', 55000)),
            'temperature': kwargs.get('temperature', self.llm_config.get('temperature', 0.7)),
            'top_p': kwargs.get('top_p', self.llm_config.get('top_p', 0.9)),
            'stop': kwargs.get('stop', self.llm_config.get('stop', [])),
            'echo': False,
        }
        return llama_kwargs
