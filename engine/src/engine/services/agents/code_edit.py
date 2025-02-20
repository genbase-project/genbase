from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Any
from diff_match_patch import diff_match_patch
from loguru import logger

@dataclass
class CodeEdit:
    """Represents a code edit with original and updated content"""
    original: str
    updated: str

@dataclass
class CodeEditResult:
    """Result of code edit operation"""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    diff: Optional[str] = None
    patches: Optional[List[str]] = None
    failed_matches: Optional[List[str]] = None

class CodeBlockEditUtil:
    def __init__(self):
        self.dmp = diff_match_patch()
        # Configure diff_match_patch settings for better code matching
        self.dmp.Diff_Timeout = 2.0
        self.dmp.Match_Threshold = 0.5
        self.dmp.Match_Distance = 1000
        self.dmp.Patch_DeleteThreshold = 0.5

    def create_patch(self, original: str, updated: str) -> List[Any]:
        """Create a patch between original and updated text"""
        diffs = self.dmp.diff_main(original, updated)
        self.dmp.diff_cleanupSemantic(diffs)
        patches = self.dmp.patch_make(original, diffs)
        return patches

    def apply_single_edit(self, content: str, edit: CodeEdit) -> Tuple[str, bool, Optional[str]]:
        """
        Apply a single edit and return the result, success status, and error
        
        Special cases:
        - If original is empty/blank and content is empty/blank: return updated content
        - If original is empty/blank and content is not: append updated content
        - Otherwise try to match and replace as normal
        """
        try:
            # Handle empty/blank original code case
            if not edit.original or edit.original.isspace():
                if not content or content.isspace():
                    # Empty content and empty original - return full updated content
                    return edit.updated, True, None
                else:
                    # Content exists but empty original - append updated
                    return f"{content}\n{edit.updated}", True, None
            
            # Regular matching logic for non-empty original
            location = content.find(edit.original)
            
            if location == -1:
                # If exact match fails, try fuzzy matching
                match_location = self.dmp.match_main(content, edit.original, 0)
                
                if match_location == -1:
                    return content, False, f"Could not find match for:\n{edit.original}"
                
                # Create and apply patch
                patches = self.create_patch(edit.original, edit.updated)
                new_content, results = self.dmp.patch_apply(patches, content)
                
                if not all(results):
                    return content, False, "Patch application failed"
                    
                return new_content, True, None
            
            # Direct replacement for exact matches
            new_content = content[:location] + edit.updated + content[location + len(edit.original):]
            return new_content, True, None
            
        except Exception as e:
            return content, False, str(e)

    def format_diff(self, original: str, updated: str) -> str:
        """Create a human-readable diff"""
        diffs = self.dmp.diff_main(original, updated)
        self.dmp.diff_cleanupSemantic(diffs)
        
        diff_text = []
        for op, text in diffs:
            if op == self.dmp.DIFF_INSERT:
                diff_text.append(f"+ {text}")
            elif op == self.dmp.DIFF_DELETE:
                diff_text.append(f"- {text}")
            elif op == self.dmp.DIFF_EQUAL:
                diff_text.append(f"  {text}")
        
        return "\n".join(diff_text)

    def apply_edits(self, content: str, edits: List[CodeEdit]) -> CodeEditResult:
        """
        Apply multiple code edits using Google's diff-match-patch
        """
        try:
            current_content = content
            failed_matches = []
            patches_applied = []
            has_changes = False
            
            for edit in edits:
                new_content, success, error = self.apply_single_edit(current_content, edit)
                
                if success:
                    if new_content != current_content:
                        has_changes = True
                        patches = self.create_patch(edit.original, edit.updated)
                        patches_applied.extend(str(p) for p in patches)
                    current_content = new_content
                else:
                    failed_matches.append(f"Failed edit: {error}")
            
            if not has_changes:
                return CodeEditResult(
                    success=False,
                    error="No changes were made",
                    content=content
                )
            
            if failed_matches:
                return CodeEditResult(
                    success=False,
                    content=current_content,
                    error="Some edits failed",
                    diff=self.format_diff(content, current_content),
                    patches=patches_applied,
                    failed_matches=failed_matches
                )
            
            return CodeEditResult(
                success=True,
                content=current_content,
                diff=self.format_diff(content, current_content),
                patches=patches_applied
            )
            
        except Exception as e:
            logger.error(f"Error applying code edits: {str(e)}")
            return CodeEditResult(success=False, error=str(e))

