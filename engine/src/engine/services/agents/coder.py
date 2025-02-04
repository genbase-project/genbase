# from dataclasses import dataclass
# from datetime import datetime, UTC
# from typing import Dict, List, Optional, Set, Tuple, Any
# from sqlalchemy import select
# from sqlalchemy.orm import Session
# import json
# from pathlib import Path
# import difflib

# from engine.db.models import ChatHistory
# from engine.db.session import SessionLocal
# from engine.config.context import Context
# from engine.services.execution.model import ModelService
# from engine.utils.logging import logger
# @dataclass
# class EditBlock:
#     """Represents a single edit block for code changes"""
#     file_path: str
#     original: str  # Original content to match
#     updated: str   # New content to replace with
#     line_number: Optional[int] = None

# @dataclass
# class FileContext:
#     """Represents contextual information about a file"""
#     path: str
#     last_modified: float
#     semantic_info: str
#     size_bytes: int

# class CoderService:
#     def __init__(self, repo_path: str, model_service: ModelService):
#         """Initialize with repo path and model service"""
#         print(f"Initializing CoderService with repo_path: {repo_path}")
#         self.repo_path = Path(repo_path)
#         self.model_service = model_service
#         self.file_contents: Dict[str, str] = {}
#         self.semantic_cache: Dict[str, FileContext] = {}
        
#         # Define tools for file operations
#         self.tools = [
#             {
#                 "type": "function",
#                 "function": {
#                     "name": "edit_file",
#                     "description": "Edit content in a file",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "file_path": {
#                                 "type": "string",
#                                 "description": "Path to the file relative to repository root"
#                             },
#                             "original": {
#                                 "type": "string",
#                                 "description": "Original content to be replaced"
#                             },
#                             "updated": {
#                                 "type": "string",
#                                 "description": "New content to replace with"
#                             },
#                             "explanation": {
#                                 "type": "string",
#                                 "description": "Explanation of why this change is being made"
#                             }
#                         },
#                         "required": ["file_path", "original", "updated", "explanation"]
#                     }
#                 }
#             }
#         ]

#     def _get_db(self) -> Session:
#         """Get database session"""
#         return SessionLocal()

#     def _get_chat_history(self, module_id: str, workflow: str) -> List[Dict[str, Any]]:
#         """Get chat history for a specific module and workflow"""
#         try:
#             with self._get_db() as db:
#                 stmt = (
#                     select(ChatHistory)
#                     .where(
#                         ChatHistory.module_id == module_id,
#                         ChatHistory.section == workflow
#                     )
#                     .order_by(ChatHistory.timestamp.asc())
#                 )
#                 messages = db.execute(stmt).scalars().all()

#                 history = []
#                 for msg in messages:
#                     message = {
#                         "role": msg.role,
#                         "content": msg.content
#                     }
#                     if msg.message_type in ["tool_call", "tool_result"]:
#                         if msg.message_type == "tool_call":
#                             message["tool_calls"] = msg.tool_data
#                         else:
#                             message["tool_results"] = msg.tool_data
#                     history.append(message)
#                 return history
#         except Exception as e:
#             raise Exception(f"Failed to get chat history: {str(e)}")

#     def _add_to_history(
#         self,
#         module_id: str,
#         role: str,
#         content: str,
#         message_type: str = "text",
#         tool_data: Optional[Any] = None
#     ):
#         """Add message to chat history"""
#         try:
#             with self._get_db() as db:
#                 chat_message = ChatHistory(
#                     module_id=module_id,
#                     section="edit",
#                     role=role,
#                     content=content or "Empty message",
#                     timestamp=datetime.now(UTC),
#                     message_type=message_type,
#                     tool_data=tool_data
#                 )
#                 db.add(chat_message)
#                 db.commit()
#         except Exception as e:
#             print(f"Failed to add message to history: {str(e)}")
#             raise

#     def _extract_pending_edit_from_history(self, messages: List[Dict[str, Any]]) -> Optional[Dict]:
#         """Extract the most recent pending edit from chat history"""
#         try:
#             for msg in reversed(messages):
#                 if msg["role"] == "assistant" and "tool_results" in msg:
#                     tool_results = msg["tool_results"]
#                     if isinstance(tool_results, list) and tool_results:
#                         result = tool_results[0].get("result", {})
#                         if "proposed_changes" in result and result["proposed_changes"]:
#                             # Check if this proposal was already applied
#                             if not any(m.get("tool_results", [{}])[0].get("result", {}).get("applied_changes", False) 
#                                      for m in messages[messages.index(msg):]):
#                                 print(f"Found pending edit: {result['proposed_changes'][0]}")
#                                 return result["proposed_changes"][0]
#             print("No pending edits found in history")
#             return None
#         except Exception as e:
#             print(f"Error extracting pending edit: {str(e)}")
#             return None

#     async def _check_confirmation(self, user_input: str) -> bool:
#         """Check if user input is confirming the changes"""
#         confirm_messages = [
#             {
#                 "role": "system",
#                 "content": """You are an AI that analyzes if users are confirming or rejecting proposed changes.
#                 Respond with 'yes' if the user appears to be agreeing, confirming, or saying yes (including variations like 'sure', 'okay', 'go ahead', etc.)
#                 Respond with 'no' for any other response.
#                 Respond with ONLY 'yes' or 'no'."""
#             },
#             {
#                 "role": "user",
#                 "content": user_input
#             }
#         ]
#         print(f"Checking confirmation for input: {user_input}")
#         confirm_response = await self.model_service.chat_completion(messages=confirm_messages)
#         confirmation = confirm_response.choices[0].message.content.lower().strip()
#         print(f"Confirmation response: {confirmation}")
#         return confirmation == 'yes'

#     async def process_request(self, module_id: str, user_input: Context) -> Dict[str, str]:
#         """Process both code modification and regular chat requests"""
#         try:
#             print(f"\nProcessing request for module {module_id}")
#             print(f"User input: {str(user_input)}")
            
#             # Get chat history
#             db_messages = self._get_chat_history(module_id, "edit")
            
#             # Check for pending edits in history
#             pending_edit = self._extract_pending_edit_from_history(db_messages)
            
#             if pending_edit:
#                 print(f"Found pending edit in history: {pending_edit}")
#                 is_confirming = await self._check_confirmation(str(user_input))
#                 print(f"Confirmation check result: {is_confirming}")
                
#                 if is_confirming:
#                     print("User confirmed changes, applying edits...")
#                     edit_block = EditBlock(
#                         file_path=pending_edit["file_path"],
#                         original=pending_edit["original"],
#                         updated=pending_edit["updated"]
#                     )
                    
#                     success = await self._apply_edit(edit_block)
#                     print(f"Edit application result: {success}")
                    
#                     response_msg = f"Changes {'applied successfully' if success else 'failed to apply'} to {edit_block.file_path}"
                    
#                     self._add_to_history(
#                         module_id=module_id,
#                         role="assistant",
#                         content=response_msg,
#                         message_type="tool_result",
#                         tool_data=[{"result": {"applied_changes": success}, "action": "edit_file"}]
#                     )
#                     return {"message": response_msg}
#                 else:
#                     print("User did not confirm changes")
#                     msg = "Changes were not applied. Let me know if you'd like to proceed with the changes or if you need any modifications."
#                     self._add_to_history(
#                         module_id=module_id,
#                         role="assistant",
#                         content=msg
#                     )
#                     return {"message": msg}

#             # Normal request processing
#             context = await self._prepare_context()
#             model_messages = [
#                 {
#                     "role": "system",
#                     "content": self._get_system_prompt(context)
#                 }
#             ]
            
#             if db_messages and db_messages[0]["role"] == "assistant":
#                 model_messages.append({"role": "user", "content": "."})
            
#             model_messages.extend(db_messages)
#             model_messages.append(user_input.to_message())
            
#             self._add_to_history(module_id, "user", str(user_input))
            
#             response = await self.model_service.chat_completion(
#                 messages=model_messages,
#                 tools=self.tools,
#                 tool_choice="auto"
#             )
            
#             assistant_message = response.choices[0].message
#             tool_calls = getattr(assistant_message, 'tool_calls', None)

#             if tool_calls:
#                 print("Processing tool calls...")
#                 tool_call = tool_calls[0]
#                 func_args = json.loads(tool_call.function.arguments)
                
#                 response_msg = (
#                     f"Proposed changes for {func_args['file_path']}:\n"
#                     "```diff\n"
#                     f"- {func_args['original'].strip()}\n"
#                     f"+ {func_args['updated'].strip()}\n"
#                     "```\n"
#                     f"\nExplanation: {func_args['explanation']}\n"
#                     "\nWould you like me to apply these changes? (Please respond with 'yes' to confirm)"
#                 )

#                 self._add_to_history(
#                     module_id=module_id,
#                     role="assistant",
#                     content=response_msg,
#                     message_type="tool_result",
#                     tool_data=[{
#                         "result": {"proposed_changes": [func_args]},
#                         "action": "edit_file"
#                     }]
#                 )
#                 return {"message": response_msg}

#             # Normal message response
#             self._add_to_history(
#                 module_id=module_id,
#                 role="assistant",
#                 content=assistant_message.content or ""
#             )
#             return {"message": assistant_message.content or ""}
            
#         except Exception as e:
#             error_msg = f"Failed to handle edit workflow: {str(e)}"
#             print(f"Error in process_request: {error_msg}")
#             raise Exception(error_msg)

#     async def _apply_edit(self, edit: EditBlock) -> bool:
#         """Apply a single edit block to a file"""
#         try:
#             print(f"Applying edit to {edit.file_path}")
        
#             file_path = self.repo_path / edit.file_path
#             file_path.parent.mkdir(parents=True, exist_ok=True)
            
#             if not file_path.exists() or not edit.original.strip():
#                 print(f"Creating new file or empty file: {file_path}")
#                 with open(file_path, 'w', encoding='utf-8') as f:
#                     f.write(edit.updated)
#                 return True
                
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 current_content = f.read()
            
#             print(f"Current file size: {len(current_content)} bytes")
            
#             matcher = difflib.SequenceMatcher(None, current_content, edit.original)
#             match = matcher.find_longest_match(0, len(current_content), 0, len(edit.original))
            
#             match_quality = match.size / len(edit.original) if edit.original else 0
#             print(f"Match quality: {match_quality}")
            
#             if not edit.original or match_quality > 0.9:
#                 new_content = (
#                     current_content[:match.a] + 
#                     edit.updated + 
#                     current_content[match.a + match.size:]
#                 )
                
#                 print(f"Writing new content to {file_path}")
#                 with open(file_path, 'w', encoding='utf-8') as f:
#                     f.write(new_content)
#                 return True
            
#             print(f"No good match found for {file_path}")
#             return False
                
#         except Exception as e:
#             print(f"Error applying edit to {edit.file_path}: {str(e)}")
#             return False

#     async def _prepare_context(self) -> str:
#         """Prepare current repository context"""
#         try:
#             repo_files = []
#             logger.info(f"Preparing context for repo: {self.repo_path}")
#             for file_path in self.repo_path.rglob('*'):
#                 if file_path.is_file() and not any(p.startswith('.') for p in file_path.parts):
#                     rel_path = file_path.relative_to(self.repo_path)
#                     repo_files.append(f"- {rel_path}")
            
#             context = "Repository structure:\n" + "\n".join(repo_files)
            
#             if self.file_contents:
#                 context += "\n\nLoaded file contents:\n"
#                 for fname, content in self.file_contents.items():
#                     context += f"\n{fname}:\n```\n{content}\n```\n"
            
#             return context
#         except Exception as e:
#             print(f"Error preparing context: {str(e)}")
#             return "Error preparing repository context"

#     def load_file(self, file_path: str) -> bool:
#         """Load a file's content into memory"""
#         try:
#             full_path = self.repo_path / file_path
#             if full_path.is_file():
#                 with open(full_path, 'r') as f:
#                     self.file_contents[file_path] = f.read()
#                 return True
#         except Exception as e:
#             print(f"Error loading file {file_path}: {str(e)}")
#             return False

#     def _get_system_prompt(self, context: str) -> str:
#         return f"""You are an expert software developer assistant.
# Current repository context:
# {context}

# When suggesting code changes:
# 1. Use the edit_file function to propose changes
# 2. Explain your changes clearly
# 3. Wait for user confirmation before applying changes

# Guidelines:
# - Make minimal necessary changes
# - Maintain code style and structure
# - Show clear diffs of proposed changes
# - Explain reasons for each modification
# """