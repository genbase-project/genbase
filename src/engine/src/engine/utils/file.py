
import os
import zipfile
from pathlib import Path

def is_safe_path(base_path: Path, file_path: str) -> bool:
    """
    Check if the file path is safe and within the repository
    """
    try:
        # Normalize path (convert windows paths, remove redundant separators)
        norm_path = os.path.normpath(file_path)
        
        # Check for absolute paths or path traversal attempts
        if (norm_path.startswith('/') or 
            norm_path.startswith('\\') or 
            norm_path.startswith('..') or 
            '..' in norm_path.split(os.sep)):
            return False
            
        # Ensure the resolved path is within the base path
        full_path = (base_path / norm_path).resolve()
        return full_path.is_file() or not full_path.exists() and full_path.parent.exists()
    except Exception:
        return False
    








def extract_zip(zip_path: Path, extract_path: Path):
    """Extract zip file to specified path"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)