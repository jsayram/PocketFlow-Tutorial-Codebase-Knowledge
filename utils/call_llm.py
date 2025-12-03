from google import genai
import os
import logging
import json
from datetime import datetime
import requests
import sys
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

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
file_handler = logging.FileHandler(log_file)
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
    logger.info(f"PROMPT: {prompt}")

    # Check cache if enabled
    if use_cache:
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
    
