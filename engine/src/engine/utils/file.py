# engine/utils/file.py
import os
import zipfile
from pathlib import Path

from loguru import logger

def is_safe_path(base_path: Path, file_path: str) -> bool:
    """
    Check if the file path is safe and within the base repository path.
    Handles both existing and non-existent (to be created) files.
    """
    try:
        base_path = base_path.resolve()
        # Normalize path (convert windows paths, remove redundant separators)
        norm_path_str = os.path.normpath(file_path)

        # Basic checks for traversal and absolute paths
        if (norm_path_str.startswith(('/', '\\', '..')) or
                '..' in norm_path_str.split(os.sep)):
            return False

        # Proposed path relative to base
        proposed_path = (base_path / norm_path_str).resolve()

        return os.path.commonpath([base_path, proposed_path]) == str(base_path)

    except Exception as e:
        logger.error(f"Error during path validation: {e}")
        return False

def extract_zip(zip_path: Path, extract_path: Path):
    """Extract zip file to specified path"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)