from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import difflib
from engine.config.workflow_config import WorkflowConfigurations
from engine.services.agents.base_agent import Action, AgentContext, AgentError, AgentServices, BaseAgent
from engine.utils.logging import logger
from engine.services.execution.workflow import WorkflowError
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import difflib
from engine.utils.logging import logger


@dataclass
class EditBlock:
    """Represents a single edit block for code changes"""
    file_path: str
    original: str  # Original content to match
    updated: str   # New content to replace with
    line_number: Optional[int] = None

@dataclass
class FileContext:
    """Represents contextual information about a file"""
    path: str
    last_modified: float
    semantic_info: str
    size_bytes: int


class CoderAgent(BaseAgent):
    """Agent for handling code modifications"""

    def __init__(self, services: AgentServices):
        super().__init__(services)
        self.file_contents: Dict[str, str] = {}
        self.repo_path: Path = ""
        self.semantic_cache: Dict[str, FileContext] = {}
        self.agent_services = services

    @property
    def agent_type(self) -> str:
        return WorkflowConfigurations.CODER_AGENT

    def _parse_edit_xml(self, xml_string: str) -> List[EditBlock]:
        """Parse edit suggestions in XML format"""
        try:
            import xml.etree.ElementTree as ET
            from io import StringIO

            # Wrap multiple edit blocks in a root element
            wrapped_xml = f"<edits>{xml_string}</edits>"
            
            # Parse XML string
            root = ET.fromstring(wrapped_xml)
            edits = []

            # Process each edit_file element
            for edit_elem in root.findall('edit_file'):
                file_path = edit_elem.get('file_path')
                if not file_path:
                    continue

                original_elem = edit_elem.find('original')
                updated_elem = edit_elem.find('updated')

                if original_elem is None or updated_elem is None:
                    continue

                original_content = original_elem.text or ""
                updated_content = updated_elem.text or ""

                edits.append(EditBlock(
                    file_path=file_path,
                    original=original_content,
                    updated=updated_content
                ))

            return edits
        except Exception as e:
            logger.error(f"Error parsing edit XML: {str(e)}")
            return []

    @property
    def default_actions(self) -> List[Action]:
        return []  # No default actions as we're using XML format

    def _get_base_instructions(self) -> str:
        return """You are an expert software developer assistant with access to the current repository context.

I can help in two ways:
1. Providing general software development guidance and explanations
2. Suggesting and applying code changes

When suggesting code changes, use the following XML format. Multiple changes can be suggested at once using multiple edit_file blocks:

<edit_file file_path="path/to/file1">
<original>
Original code to be replaced in first file
</original>
<updated>
Updated code for first file
</updated>
</edit_file>

<edit_file file_path="path/to/file2">
<original>
Original code to be replaced in second file
</original>
<updated>
Updated code for second file
</updated>
</edit_file>

Each edit_file block should have a unique file_path. Multiple changes to the same file should also use separate edit_file blocks. Always explain changes clearly and wait for user confirmation before applying changes. All changes will be applied or rejected together.

For general assistance:
- I provide clear, technical explanations based on the repository context
- I understand and can explain the project structure
- I share coding best practices and patterns
- I help troubleshoot issues
- I answer software development questions
- I can describe and list files in the repository

Guidelines:
- Make minimal necessary changes when editing code
- Maintain code style and structure
- Show clear diffs of proposed changes
- Explain reasons for each modification
- Provide clear, technical responses to questions
- Use the repository context provided to understand the project structure
- When asked about files or project structure, refer to the repository context

Repository Context:
- At the start of each conversation, I receive a complete list of files in the repository
- I should use this context to answer questions about files and project structure
- I should NOT claim I don't have access to file information
"""

    async def _process_workflow(
        self,
        context: AgentContext,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process both code modification and general assistance requests"""
        try:
            module_metadata = self.agent_services.module_service.get_module_metadata(context.module_id)
            self.repo_path = self.agent_services.repo_service._get_repo_path(module_metadata.repo_name)

            # First, check for pending edits since they take priority
            pending_edits = self._extract_pending_edits(context.module_id)
            
            if pending_edits:  # Handle pending edit confirmation flow
                logger.info(f"Found {len(pending_edits)} pending edits")
                is_confirming = await self._check_confirmation(context.user_input)
                
                if is_confirming:
                    logger.info("User confirmed changes, applying edits...")
                    results = []
                    for edit in pending_edits:
                        success = await self._apply_edit(edit)
                        results.append((edit.file_path, success))
                    
                    # Prepare response message
                    success_files = [f for f, s in results if s]
                    failed_files = [f for f, s in results if not s]
                    
                    response_parts = []
                    if success_files:
                        response_parts.append(f"Changes applied successfully to: {', '.join(success_files)}")
                    if failed_files:
                        response_parts.append(f"Failed to apply changes to: {', '.join(failed_files)}")
                    
                    response_msg = ". ".join(response_parts) or "No changes were applied"

                    # Add result to history
                    self.history_manager.add_to_history(
                        module_id=context.module_id,
                        workflow=context.workflow,
                        role="assistant",
                        content=response_msg
                    )
                    return {"response": response_msg, "results": []}
                else:
                    msg = "Changes were not applied. Let me know if you'd like to proceed with the changes or if you need any modifications."
                    self.history_manager.add_to_history(
                        module_id=context.module_id,
                        workflow=context.workflow,
                        role="assistant",
                        content=msg
                    )
                    return {"response": msg, "results": []}

            # Prepare context for normal processing
            repo_context = await self._prepare_context()
            
            try:
                # Get workflow metadata and instructions
                workflow_data = await self.get_combined_workflow_metadata(context)
            except WorkflowError as e:
                # If we can't get workflow metadata, use empty data but log the error
                logger.warning(f"Could not get workflow metadata: {str(e)}")
                workflow_data = {
                    "instructions": "",
                    "actions": [],
                    "requirements": []
                }
            
            # Add workflow instructions and repo context to messages
            messages = self._add_instruction_prompts(messages, workflow_data, context)
            
            # Add repository context
            for msg in messages:
                if msg["role"] == "system":
                    msg["content"] = f"{msg['content']}\n\nCurrent repository context:\n{repo_context}"
                    break

            # Get model response 
            response = await self.services.model_service.chat_completion(
                messages=messages,
                tools=[]  # No tools needed since using XML format
            )
            
            assistant_message = response.choices[0].message
            logger.info(f"Last message: {messages[-1]}")
            logger.info(f"Assistant response: {assistant_message.content}")
            content = assistant_message.content or ""

            # Add message to history
            self.history_manager.add_to_history(
                module_id=context.module_id,
                workflow=context.workflow,
                role="assistant",
                content=content
            )

            # Return the response (which may contain XML edit suggestion)
            return {"response": content, "results": []}
            
        except Exception as e:
            logger.error(f"Error in process_workflow: {str(e)}")
            raise AgentError(f"Failed to process workflow: {str(e)}")
        
    def _extract_pending_edits(self, module_id: str) -> List[EditBlock]:
        """Extract all pending edits from chat history"""
        try:
            messages = self.history_manager.get_chat_history(module_id, "edit")
            
            for msg in reversed(messages):
                if msg["role"] == "assistant" and msg.get("content"):
                    content = msg["content"]
                    # Look for XML edit blocks in the message content
                    if "<edit_file" in content:
                        # Check if these proposals were already applied
                        if not any(m.get("content", "").startswith("Changes applied successfully") 
                                 for m in messages[messages.index(msg):]):
                            # Parse using the same method as _parse_edit_xml
                            return self._parse_edit_xml(content)
            return []
        except Exception as e:
            logger.error(f"Error extracting pending edits: {str(e)}")
            return []

    async def _check_confirmation(self, user_input: str) -> bool:
        """Check if user input is confirming the changes"""
        confirm_messages = [
            {
                "role": "system",
                "content": """You are an AI that analyzes if users are confirming or rejecting proposed changes.
                Respond with 'yes' if the user appears to be agreeing, confirming, or saying yes (including variations like 'sure', 'okay', 'go ahead', etc.)
                Respond with 'no' for any other response.
                Respond with ONLY 'yes' or 'no'."""
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
        
        confirm_response = await self.services.model_service.chat_completion(
            messages=confirm_messages,
            tools=[]  # Empty array instead of None
        )
        confirmation = confirm_response.choices[0].message.content.lower().strip()
        return confirmation == 'yes'

    async def _apply_edit(self, edit: EditBlock) -> bool:
        """Apply a single edit block to a file"""
        try:
            logger.info(f"Applying edit to {edit.file_path}")
            file_path = self.repo_path / edit.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not file_path.exists() or not edit.original.strip():
                logger.info(f"Creating new file or empty file: {file_path}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(edit.updated)
                return True
                
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            matcher = difflib.SequenceMatcher(None, current_content, edit.original)
            match = matcher.find_longest_match(0, len(current_content), 0, len(edit.original))
            
            match_quality = match.size / len(edit.original) if edit.original else 0
            logger.info(f"Match quality: {match_quality}")
            
            if not edit.original or match_quality > 0.9:
                new_content = (
                    current_content[:match.a] + 
                    edit.updated + 
                    current_content[match.a + match.size:]
                )
                
                logger.info(f"Writing new content to {file_path}")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
            
            logger.info(f"No good match found for {file_path}")
            return False
                
        except Exception as e:
            logger.error(f"Error applying edit to {edit.file_path}: {str(e)}")
            return False

    async def _prepare_context(self) -> str:
        """Prepare current repository context"""
        try:
            directories = []
            files = []
            logger.info("Repo path is: "+str(self.repo_path))
            for file_path in self.repo_path.rglob('*'):
                # Skip .git directory
                if '.git' in file_path.parts:
                    continue
                    
                rel_path = file_path.relative_to(self.repo_path)
                
                if file_path.is_dir():
                    directories.append(f"- {rel_path}/ (directory)")
                else:
                    files.append(f"- {rel_path} (file) content: {file_path.read_text()}")
            
            # Sort directories and files separately
            directories.sort()
            files.sort()
            
            context = """Repository structure:
The following is a complete list of files and directories in the repository. Each entry shows:
- Full path relative to repository root
- Type (file or directory)

Directories:
""" + "\n".join(directories) + "\n\nFiles:\n" + "\n".join(files)
            


            if self.file_contents:
                context += "\n\nLoaded file contents:\n"
                for fname, content in self.file_contents.items():
                    context += f"\n{fname}:\n```\n{content}\n```\n"
            

            return context
        except Exception as e:
            logger.error(f"Error preparing context: {str(e)}")
            return "Error preparing repository context"

    def load_file(self, file_path: str) -> bool:
        """Load a file's content into memory"""
        try:
            full_path = self.repo_path / file_path
            if full_path.is_file():
                with open(full_path, 'r') as f:
                    self.file_contents[file_path] = f.read()
                return True
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {str(e)}")
            return False
