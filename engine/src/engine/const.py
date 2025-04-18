# Configuration
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger



load_dotenv()


BASE_DATA_DIR = Path(os.getenv("DATA_DIR"))
REPO_BASE_DIR = BASE_DATA_DIR / "workspaces"
KIT_BASE_DIR = BASE_DATA_DIR / "kits"
VENV_BASE_DIR = BASE_DATA_DIR / "venvs"
RPC_PORT = int(os.getenv("RPC_PORT", 18861))












# --- Configuration Loading for Supported Content Types ---
SUPPORTED_CONTENT_TYPES_DEFINITION = {}
SUPPORTED_MIME_TYPES_LIST = []
try:
    # Determine config file path (adjust if needed)
    config_path = Path(__file__).parent / "supported_content_types.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            SUPPORTED_CONTENT_TYPES_DEFINITION = json.load(f)
            SUPPORTED_MIME_TYPES_LIST = [
                item.get("type")
                for item in SUPPORTED_CONTENT_TYPES_DEFINITION.get("supported_content_types", [])
                if item.get("type") # Ensure mime_type exists
            ]
        logger.info(f"Loaded {len(SUPPORTED_MIME_TYPES_LIST)} supported content types from {config_path}")
    else:
        logger.warning(f"Supported content types config file not found at {config_path}. Using empty list.")
except (json.JSONDecodeError, IOError) as e:
    logger.error(f"Failed to load or parse supported_content_types.json: {e}")
except Exception as e:
    logger.error(f"Unexpected error loading supported content types config: {e}")
# --- End Configuration Loading ---
