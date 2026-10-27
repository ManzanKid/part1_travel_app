import os
from pathlib import Path
from dotenv import load_dotenv

# Find the project root based on this file's location.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Load the project's .env file.
load_dotenv(dotenv_path=ENV_PATH)


def geoapify_config_status():
    api_key = os.getenv("GEOAPIFY_API_KEY", "")

    if api_key.strip():
        return "key is configured"

    return "key is not configured"
def get_geoapify_api_key():
    return os.getenv("GEOAPIFY_API_KEY", "").strip()