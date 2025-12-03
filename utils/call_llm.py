"""
LLM Wrapper - Supports multiple providers (Gemini, OpenAI, OpenRouter, and generic OpenAI-compatible APIs)
"""

from google import genai
import os
import logging
import json
import requests
import sys
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_directory = os.getenv("LOG_DIR", "logs")
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(
    log_directory, f"llm_calls_{datetime.now().strftime('%Y%m%d')}.log"
)

# Set up logger
logger = logging.getLogger("llm_logger")
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent propagation to root logger

# Only add handler if not already present
if not logger.handlers:
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

# Simple cache configuration
cache_file = "llm_cache.json"


def load_cache() -> dict:
    """Load cache from disk."""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
    return {}


def save_cache(cache: dict) -> None:
    """Save cache to disk."""
    try:
        with open(cache_file, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def get_llm_provider() -> str:
    """
    Determine which LLM provider to use based on environment variables.
    
    Priority:
    1. GEMINI_API_KEY or GEMINI_PROJECT_ID -> "GEMINI"
    2. OPENROUTER_API_KEY -> "OPENROUTER"
    3. OPENAI_API_KEY -> "OPENAI"
    4. LLM_API_BASE_URL -> "GENERIC"
    """
    if os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_PROJECT_ID"):
        return "GEMINI"
    elif os.getenv("OPENROUTER_API_KEY"):
        return "OPENROUTER"
    elif os.getenv("OPENAI_API_KEY"):
        return "OPENAI"
    elif os.getenv("LLM_API_BASE_URL"):
        return "GENERIC"
    else:
        raise ValueError(
            "No LLM provider configured. Set one of: "
            "GEMINI_API_KEY, GEMINI_PROJECT_ID, OPENROUTER_API_KEY, "
            "OPENAI_API_KEY, or LLM_API_BASE_URL"
        )


def call_llm(prompt: str, use_cache: bool = True) -> str:
    """
    Main LLM calling function that routes to the appropriate provider.
    
    Args:
        prompt: The prompt to send to the LLM
        use_cache: Whether to use caching (default: True)
        
    Returns:
        The LLM response text
    """
    logger.info(f"PROMPT: {prompt}")

    # Check cache if enabled
    if use_cache:
        cache = load_cache()
        if prompt in cache:
            logger.info("CACHE HIT: Using cached response")
            return cache[prompt]

    # Get provider and call appropriate function
    provider = get_llm_provider()
    
    if provider == "GEMINI":
        response_text = _call_llm_gemini(prompt)
    elif provider == "OPENROUTER":
        response_text = _call_llm_openrouter(prompt)
    elif provider == "OPENAI":
        response_text = _call_llm_openai(prompt)
    else:  # GENERIC - OpenAI-compatible API
        response_text = _call_llm_generic(prompt)

    logger.info(f"RESPONSE: {response_text}")

    # Update cache if enabled
    if use_cache:
        cache = load_cache()
        cache[prompt] = response_text
        save_cache(cache)

    return response_text


def _call_llm_gemini(prompt: str) -> str:
    """Call Google Gemini API."""
    if os.getenv("GEMINI_PROJECT_ID"):
        client = genai.Client(
            vertexai=True,
            project=os.getenv("GEMINI_PROJECT_ID"),
            location=os.getenv("GEMINI_LOCATION", "us-central1")
        )
    elif os.getenv("GEMINI_API_KEY"):
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    else:
        raise ValueError("Either GEMINI_PROJECT_ID or GEMINI_API_KEY must be set")
    
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
    response = client.models.generate_content(
        model=model,
        contents=[prompt]
    )
    return response.text


def _call_llm_openai(prompt: str) -> str:
    """Call OpenAI API directly."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("OpenAI package not installed. Run: pip install openai")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    return response.choices[0].message.content


def _call_llm_openrouter(prompt: str) -> str:
    """Call OpenRouter API."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
    base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "https://github.com"),
        "X-Title": os.getenv("OPENROUTER_TITLE", "PocketFlow Tutorial Generator")
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    
    response = requests.post(base_url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _call_llm_generic(prompt: str) -> str:
    """Call a generic OpenAI-compatible API (e.g., Ollama, local models)."""
    base_url = os.getenv("LLM_API_BASE_URL", "http://localhost:11434")
    api_key = os.getenv("LLM_API_KEY", "")  # Optional for local models
    model = os.getenv("LLM_MODEL", "llama2")
    
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error calling LLM API at {url}: {e}")


if __name__ == "__main__":
    """Test the LLM configuration."""
    try:
        provider = get_llm_provider()
        print(f"Using LLM provider: {provider}")
        
        test_prompt = "Say hello in one sentence."
        print(f"Testing with prompt: {test_prompt}")
        
        response = call_llm(test_prompt, use_cache=False)
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
