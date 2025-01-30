import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import git
from bigtree import list_to_tree, print_tree
import json

class CoderUtil:
    def __init__(self, root_path: str):
        """
        Initialize the FileService with a root directory path.
        
        Args:
            root_path (str): The root directory path to work with
        """
        self.root_path = Path(root_path).resolve()
        self._validate_directory()
        
    def _validate_directory(self) -> None:
        """Validate that the root directory exists"""
        if not self.root_path.exists():
            raise ValueError(f"Directory {self.root_path} does not exist")
            
    def _is_git_repo(self, path: Path) -> bool:
        """Check if the given path is within a git repository"""
        try:
            _ = git.Repo(path, search_parent_directories=True)
            return True
        except git.InvalidGitRepositoryError:
            return False
            
    def get_file_contents(self, max_size_kb: int = 100) -> Dict[str, Tuple[str, int]]:
        """
        Get contents of all files under root_path that are smaller than max_size_kb.
        
        Args:
            max_size_kb (int): Maximum file size in KB (default: 100)
            
        Returns:
            Dict[str, Tuple[str, int]]: Dictionary with relative paths as keys and tuples of (content, size_in_bytes) as values
        """
        max_size_bytes = max_size_kb * 1024
        contents = {}
        
        for root, _, files in os.walk(self.root_path):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.root_path)
                
                # Skip git internal files
                if '.git' in str(file_path):
                    continue
                    
                try:
                    size = file_path.stat().st_size
                    if size <= max_size_bytes:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            contents[str(rel_path)] = (f.read(), size)
                except (PermissionError, UnicodeDecodeError):
                    continue
                    
        return contents
        
    def _build_tree_dict(self) -> dict:
        """
        Build a nested dictionary representing the directory structure
        """
        tree_dict = {}
        
        for root, dirs, files in os.walk(self.root_path):
            if '.git' in root:
                continue
                
            rel_root = Path(root).relative_to(self.root_path)
            current_dict = tree_dict
            
            # Navigate to current directory in tree
            if str(rel_root) != '.':
                for part in rel_root.parts:
                    if part not in current_dict:
                        current_dict[part] = {}
                    current_dict = current_dict[part]
            
            # Add directories
            for d in sorted(dirs):
                if '.git' not in d:
                    current_dict[d] = {}
            
            # Add files
            for f in sorted(files):
                if '.git' not in f:
                    current_dict[f] = None
                    
        return tree_dict
        
    def _generate_tree(self, tree_dict: dict, prefix: str = '') -> str:
        """
        Generate a string representation of the tree structure using ASCII characters
        """
        lines = []
        items = list(tree_dict.items())
        
        for i, (name, subtree) in enumerate(items):
            is_last = i == len(items) - 1
            connector = '└─ ' if is_last else '├─ '
            lines.append(prefix + connector + name)
            
            if isinstance(subtree, dict):
                extension = '    ' if is_last else '│   '
                subtree_lines = self._generate_tree(subtree, prefix + extension)
                lines.append(subtree_lines)
                
        return '\n'.join(filter(None, lines))
        
    def get_directory_structure(self) -> str:
        """
        Get the directory structure with ASCII tree representation.
        
        Returns:
            str: String representation of the directory tree with ASCII characters
        """
        tree_dict = self._build_tree_dict()
        if not tree_dict:
            return "Empty directory"
            
        return self._generate_tree(tree_dict)
        
    def read_file(self, relative_path: str) -> Tuple[str, int]:
        """
        Read contents of a specific file using its relative path from root.
        
        Args:
            relative_path (str): Relative path from root directory
            
        Returns:
            Tuple[str, int]: Tuple containing (file_content, file_size_in_bytes)
        """
        file_path = self.root_path / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"File {relative_path} not found")
            
        size = file_path.stat().st_size
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content, size
        
    def write_file(self, relative_path: str, content: str) -> int:
        """
        Write content to a specific file using its relative path from root.
        
        Args:
            relative_path (str): Relative path from root directory
            content (str): Content to write to the file
            
        Returns:
            int: Size of the written file in bytes
        """
        file_path = self.root_path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return file_path.stat().st_size
        
    def get_file_info(self, relative_path: str) -> Dict[str, any]:
        """
        Get detailed information about a specific file.
        
        Args:
            relative_path (str): Relative path from root directory
            
        Returns:
            Dict[str, any]: Dictionary containing file information
        """
        file_path = self.root_path / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"File {relative_path} not found")
            
        stat = file_path.stat()
        return {
            "size_bytes": stat.st_size,
            "created_at": stat.st_ctime,
            "modified_at": stat.st_mtime,
            "is_binary": self._is_binary(file_path),
            "extension": file_path.suffix,
            "in_git_repo": self._is_git_repo(file_path)
        }
        
    def _is_binary(self, file_path: Path) -> bool:
        """Check if a file is binary"""
        try:
            with open(file_path, 'tr') as f:
                f.read(1024)
            return False
        except UnicodeDecodeError:
            return True


# # Example usage:
# if __name__ == "__main__":
#     # Initialize service with a directory
#     service = FileService("/root/development/hivon/engine/.data/repositories/c06e1856-76a6-4839-adcd-5c321f9ea09e")
    
#     # Get all file contents
#     contents = service.get_file_contents(max_size_kb=100)
#     print(f"Found {len(contents)} files under 100KB")
    
#     # Print directory structure
#     print("\nDirectory structure:")
#     print(service.get_directory_structure())
    
#     # Read a specific file
#     try:
#         content, size = service.read_file("test/bing.py")
#         print(f"\nFile size: {size} bytes")
#         print("Content preview:", content[:100])
#     except FileNotFoundError as e:
#         print(f"Error: {e}")
        
#     # Write to a file
#     new_size = service.write_file("output/test.txt", "Hello, World!")
#     print(f"\nWrote {new_size} bytes to test.txt")
    
#     # Get file info
#     try:
#         info = service.get_file_info("test/bing.py")
#         print("\nFile info:", json.dumps(info, indent=2))
#     except FileNotFoundError as e:
#         print(f"Error: {e}")
