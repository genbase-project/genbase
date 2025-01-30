from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re
from pathlib import Path
import difflib

@dataclass
class EditBlock:
    """Represents a single edit block for code changes"""
    file_path: str
    original: str  # Original content to match
    updated: str   # New content to replace with
    line_number: Optional[int] = None

class EditBlockParser:
    """Parser for edit blocks in LLM responses"""
    
    def __init__(self, fence_start="```", fence_end="```"):
        self.fence_start = fence_start
        self.fence_end = fence_end
        
    def parse_edit_blocks(self, content: str) -> List[EditBlock]:
        """Parse edit blocks from model response"""
        blocks = []
        lines = content.splitlines()
        current_file = None
        in_block = False
        block_type = None
        current_content = []
        
        for line in lines:
            if not in_block:
                # Look for filename and opening fence
                if line.strip() and not line.startswith(self.fence_start):
                    current_file = self._clean_filename(line)
                elif line.startswith(self.fence_start):
                    in_block = True
                    block_type = 'original'
            else:
                if line.startswith('======='):
                    # Switch from original to updated content
                    original_content = '\n'.join(current_content)
                    current_content = []
                    block_type = 'updated'
                elif line.startswith(self.fence_end):
                    # End of block
                    updated_content = '\n'.join(current_content)
                    if current_file and original_content:
                        blocks.append(EditBlock(
                            file_path=current_file,
                            original=original_content,
                            updated=updated_content
                        ))
                    in_block = False
                    current_content = []
                    current_file = None
                else:
                    current_content.append(line)
                    
        return blocks

    def _clean_filename(self, filename: str) -> str:
        """Clean and validate filename"""
        filename = filename.strip()
        # Remove common markers
        for prefix in ['File:', '#', '/*']:
            if filename.startswith(prefix):
                filename = filename[len(prefix):].strip()
        # Remove suffix markers
        for suffix in [':', '*/']:
            if filename.endswith(suffix):
                filename = filename[:-len(suffix)].strip()
        return filename

class EditApplier:
    """Applies edits to files safely using search/replace"""
    
    @staticmethod
    def find_best_match(content: str, search: str) -> Tuple[int, int, float]:
        """Find best matching location for the search string"""
        # Use difflib to find closest match
        matcher = difflib.SequenceMatcher(None, content, search)
        match = matcher.find_longest_match(0, len(content), 0, len(search))
        
        if match.size > 0:
            return match.a, match.a + match.size, match.size / len(search)
        return -1, -1, 0.0

    async def _apply_edit(self, edit: EditBlock) -> bool:
        """Apply a single edit block to a file"""
        try:
            file_path = self.repo_path / edit.file_path
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read current content if file exists, or use empty string for new files
            current_content = ""
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_content = f.read()

            # For empty/new files, just write the updated content
            if not current_content or not edit.original.strip():
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(edit.updated)
                return True

            # For existing files, find and replace content
            matcher = difflib.SequenceMatcher(None, current_content, edit.original)
            match = matcher.find_longest_match(0, len(current_content), 0, len(edit.original))
            
            if match.size > 0 and match.size / len(edit.original) > 0.9:
                new_content = (
                    current_content[:match.a] + 
                    edit.updated + 
                    current_content[match.a + match.size:]
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
            
            # If no match found but file is empty/new, write the updated content
            if not current_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(edit.updated)
                return True
                
            return False
            
        except Exception as e:
            print(f"Error applying edit to {edit.file_path}: {str(e)}")
            return False

    def validate_edit(self, original: str, edited: str) -> bool:
        """Validate that edit maintains code structure"""
        # Add validation rules here
        return True