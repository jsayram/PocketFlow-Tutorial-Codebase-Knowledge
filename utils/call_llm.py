from google import genai
import os
import logging
import json
import requests
<<<<<<< HEAD
import sys
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
=======
from datetime import datetime
>>>>>>> c8a8ca17180ca5bd18948e05aa0d2c1920f50363

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
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

# Simple cache configuration
cache_file = "llm_cache.json"

### VERIFY API KEY LOADED
# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

<<<<<<< HEAD
def ensure_api_key():
    """
    Ensures the OpenAI API key is available in environment variables.
    Loads from .env file if present and checks for the key.
    
    Returns:
        str: The API key if found
        
    Raises:
        Exception: If API key is not found after attempting to load it
    """
    # First, try to find and load the .env file from multiple possible locations
    env_locations = [
        '.env',                                  # Current directory
        '../.env',                               # Parent directory
        os.path.join(os.path.dirname(__file__), '../.env'),  # Project root relative to this script
        os.path.expanduser('~/.env')             # Home directory
    ]
    
    # Try each location
    env_loaded = False
    for env_path in env_locations:
        if os.path.exists(env_path):
            logger.info(f"Found .env file at {env_path}")
            load_dotenv(env_path)
            env_loaded = True
            break
    
    # If no .env file was found, try to find one automatically
    if not env_loaded:
        logger.info("No .env file found in standard locations, searching...")
        env_path = find_dotenv(usecwd=True)
        if env_path:
            logger.info(f"Found .env file at {env_path}")
            load_dotenv(env_path)
            env_loaded = True
        else:
            logger.warning("No .env file found")
    
    # Check if the key exists in environment variables now
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Check common variants of the key name
        for key_name in ["OPEN_AI_API_KEY", "OPENAI_KEY", "OPENROUTER_API_KEY"]:
            logger.info(f"OPENAI_API_KEY not found, checking {key_name}...")
            api_key = os.environ.get(key_name)
            if api_key:
                logger.info(f"Using {key_name} instead of OPENAI_API_KEY")
                os.environ["OPENAI_API_KEY"] = api_key
                break
    
    # If still no API key, provide help
    if not api_key:
        logger.error("No OpenAI API key found in environment variables")
        print("\n" + "="*50)
        print("API KEY CONFIGURATION ERROR")
        print("="*50)
        print("\nYour .env file should contain:")
        print("\nOPENAI_API_KEY=sk-your-key-here")
        print("\nLocation of .env file should be in the project root directory")
        print("\nCurrent working directory:", os.getcwd())
        print("\nThe following .env file locations were checked:")
        for path in env_locations:
            if os.path.exists(path):
                print(f" - {path} (EXISTS)")
            else:
                print(f" - {path} (not found)")
        
        print("\nEnvironment variables currently set:")
        for key in sorted(os.environ.keys()):
            if "KEY" in key or "API" in key or "TOKEN" in key:
                # Show partial key for debugging (sensitive but useful)
                value = os.environ[key]
                if len(value) > 10:
                    masked_value = value[:4] + "..." + value[-4:]
                else:
                    masked_value = "[too short to display safely]"
                print(f" - {key}: {masked_value}")
        
        raise Exception("OPENAI_API_KEY not set in environment variables after loading .env file")
    
    return api_key

OPEN_AI_MODEL = os.getenv("OPEN_AI_MODEL", "gpt-3.5-turbo")

def call_llm(prompt, model=OPEN_AI_MODEL, temperature=0.2, max_tokens=4096, use_cache=True):
    """
    Makes an API call to OpenAI with caching support.
    
    Args:
        prompt (str): The prompt to send
        model (str): OpenAI model identifier (default: "gpt-3.5-turbo")
        temperature (float): Sampling temperature (0.0-1.0)
        max_tokens (int): Maximum tokens to generate
        use_cache (bool): Whether to use caching
        
    Returns:
        str: Model response text
    """
    # Log the prompt (assuming logger is defined)
=======
def load_cache():
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except:
        logger.warning(f"Failed to load cache.")
    return {}


def save_cache(cache):
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
    except:
        logger.warning(f"Failed to save cache")


def get_llm_provider():
    provider = os.getenv("LLM_PROVIDER")
    if not provider and (os.getenv("GEMINI_PROJECT_ID") or os.getenv("GEMINI_API_KEY")):
        provider = "GEMINI"
    # if necessary, add ANTHROPIC/OPENAI
    return provider


def _call_llm_provider(prompt: str) -> str:
    """
    Call an LLM provider based on environment variables.
    Environment variables:
    - LLM_PROVIDER: "OLLAMA" or "XAI"
    - <provider>_MODEL: Model name (e.g., OLLAMA_MODEL, XAI_MODEL)
    - <provider>_BASE_URL: Base URL without endpoint (e.g., OLLAMA_BASE_URL, XAI_BASE_URL)
    - <provider>_API_KEY: API key (e.g., OLLAMA_API_KEY, XAI_API_KEY; optional for providers that don't require it)
    The endpoint /v1/chat/completions will be appended to the base URL.
    """
    logger.info(f"PROMPT: {prompt}") # log the prompt

    # Read the provider from environment variable
    provider = os.environ.get("LLM_PROVIDER")
    if not provider:
        raise ValueError("LLM_PROVIDER environment variable is required")

    # Construct the names of the other environment variables
    model_var = f"{provider}_MODEL"
    base_url_var = f"{provider}_BASE_URL"
    api_key_var = f"{provider}_API_KEY"

    # Read the provider-specific variables
    model = os.environ.get(model_var)
    base_url = os.environ.get(base_url_var)
    api_key = os.environ.get(api_key_var, "")  # API key is optional, default to empty string

    # Validate required variables
    if not model:
        raise ValueError(f"{model_var} environment variable is required")
    if not base_url:
        raise ValueError(f"{base_url_var} environment variable is required")

    # Append the endpoint to the base URL
    url = f"{base_url.rstrip('/')}/v1/chat/completions"

    # Configure headers and payload based on provider
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:  # Only add Authorization header if API key is provided
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response_json = response.json() # Log the response
        logger.info("RESPONSE:\n%s", json.dumps(response_json, indent=2))
        #logger.info(f"RESPONSE: {response.json()}")
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP error occurred: {e}"
        try:
            error_details = response.json().get("error", "No additional details")
            error_message += f" (Details: {error_details})"
        except:
            pass
        raise Exception(error_message)
    except requests.exceptions.ConnectionError:
        raise Exception(f"Failed to connect to {provider} API. Check your network connection.")
    except requests.exceptions.Timeout:
        raise Exception(f"Request to {provider} API timed out.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"An error occurred while making the request to {provider}: {e}")
    except ValueError:
        raise Exception(f"Failed to parse response as JSON from {provider}. The server might have returned an invalid response.")

# By default, we Google Gemini 2.5 pro, as it shows great performance for code understanding
def call_llm(prompt: str, use_cache: bool = True) -> str:
    # Log the prompt
>>>>>>> c8a8ca17180ca5bd18948e05aa0d2c1920f50363
    logger.info(f"PROMPT: {prompt}")

    # Check cache if enabled
    if use_cache:
<<<<<<< HEAD
        cache = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    cache = json.load(f)
                if prompt in cache:
                    logger.info(f"CACHE HIT: Using cached response")
                    return cache[prompt]
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")

    try:
        from openai import OpenAI
        
        # Get API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize client
        client = OpenAI(api_key=api_key)
        
        # Make API call with only supported parameters
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extract response text
        response_text = response.choices[0].message.content
        
        # Update cache if enabled
        if use_cache:
            cache = {}
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r") as f:
                        cache = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load existing cache: {e}")
            
            cache[prompt] = response_text
            try:
                with open(cache_file, "w") as f:
                    json.dump(cache, f)
            except Exception as e:
                logger.error(f"Failed to save cache: {e}")
        
        return response_text
        
    except ImportError:
        logger.error("OpenAI package not installed")
        raise ImportError("OpenAI package not installed. Run: pip install openai")
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        raise

=======
        # Load cache from disk
        cache = load_cache()
        # Return from cache if exists
        if prompt in cache:
            logger.info(f"RESPONSE: {cache[prompt]}")
            return cache[prompt]

    provider = get_llm_provider()
    if provider == "GEMINI":
        response_text = _call_llm_gemini(prompt)
    else:  # generic method using a URL that is OpenAI compatible API (Ollama, ...)
        response_text = _call_llm_provider(prompt)

    # Log the response
    logger.info(f"RESPONSE: {response_text}")

    # Update cache if enabled
    if use_cache:
        # Load cache again to avoid overwrites
        cache = load_cache()
        # Add to cache and save
        cache[prompt] = response_text
        save_cache(cache)

    return response_text


def _call_llm_gemini(prompt: str) -> str:
    if os.getenv("GEMINI_PROJECT_ID"):
        client = genai.Client(
            vertexai=True,
            project=os.getenv("GEMINI_PROJECT_ID"),
            location=os.getenv("GEMINI_LOCATION", "us-central1")
        )
    elif os.getenv("GEMINI_API_KEY"):
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    else:
        raise ValueError("Either GEMINI_PROJECT_ID or GEMINI_API_KEY must be set in the environment")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
    response = client.models.generate_content(
        model=model,
        contents=[prompt]
    )
    return response.text
>>>>>>> c8a8ca17180ca5bd18948e05aa0d2c1920f50363

if __name__ == "__main__":
    try:
        # Try to load API key from .env file
        api_key = ensure_api_key()
        
        # If we get here, the key was found
        print("API key loaded successfully!")
        key_preview = api_key[:4] + "..." + api_key[-4:]
        print(f"Using API key: {key_preview}")
        
        test_prompt = "are you able to work, also how are you?"

        # First call - should hit the API
        print("Making call...")
        response1 = call_llm(test_prompt, use_cache=False)
        print(f"Response: {response1}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
