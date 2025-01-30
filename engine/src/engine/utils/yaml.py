from pathlib import Path
import yaml
from typing import Dict, Any

class YAMLError(Exception):
    """Base exception for YAML operations"""
    pass

class YAMLUtils:
    """Utility class for YAML operations"""
    
    @staticmethod
    def read_kit(module_path: Path) -> Dict[str, Any]:
        """
        Read and parse kit.yaml from a module path
        
        Args:
            module_path: Path to module directory containing kit.yaml
            
        Returns:
            dict: Parsed kit.yaml content
            
        Raises:
            YAMLError: If file not found or parsing fails
        """
        kit_path = module_path / "kit.yaml"
        
        if not kit_path.exists():
            raise YAMLError("kit.yaml not found")
            
        try:
            with open(kit_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise YAMLError(f"Failed to parse kit.yaml: {str(e)}")