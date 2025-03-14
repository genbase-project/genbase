# Configuration
import os
from pathlib import Path

from dotenv import load_dotenv



load_dotenv()


BASE_DATA_DIR = Path(os.getenv("DATA_DIR"))
REPO_BASE_DIR = BASE_DATA_DIR / "repositories"
KIT_BASE_DIR = BASE_DATA_DIR / "kit"
