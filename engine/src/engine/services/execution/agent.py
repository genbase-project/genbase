# import json
# from dataclasses import dataclass
# from datetime import datetime, UTC
# from typing import Any, Dict, List, Optional, Tuple
# from sqlalchemy import select
# from engine.db.models import ChatHistory
# from engine.db.session import SessionLocal
# from engine.config.context import Context, Role
# from engine.services.agents.coder import CoderService
# from engine.services.core.module import ModuleService, RelationType
# from engine.services.execution.model import ModelService
# from engine.services.execution.stage_state import (
#     PROMOTE_TOOL_SCHEMA,
#     AgentStage,
#     AgentState,
#     StageStateService,
# )
# from sqlalchemy.orm import Session
# from engine.services.execution.workflow import ActionInfo, WorkflowService
# from engine.services.storage.repository import RepoService
# from engine.utils.logging import logger


# @dataclass
# class ChatMessage:
#     """Chat message structure"""
#     role: str
#     content: str
#     timestamp: str
#     message_type: str = "text"  # Can be "text", "tool_call", or "tool_result"
#     tool_data: Optional[Dict[str, Any]] = None

# class AgentError(Exception):
#     """Base exception for AI workflow operations"""
#     pass


# valid_workflows = {
#             AgentStage.INITIALIZE: ["initialize"],
#             AgentStage.MAINTAIN: ["maintain", "edit"],
#             AgentStage.REMOVE: ["remove"]
#         }


# class AgentService:
#     """Service for managing AI-driven workflow executions"""

#     def __init__(
#         self,
#         workflow_service: WorkflowService,
#         model_service: ModelService,
#         stage_state_service: StageStateService,
#         repo_service: RepoService,
#         module_service: ModuleService
#     ):
#         self.workflow_service = workflow_service
#         self.model_service = model_service

#         self.tool_to_operation_map = {}
#         self.stage_state_service = stage_state_service
#         self.repo_service = repo_service
#         self.module_service = module_service


#     def _get_db(self) -> Session:
#         """Get database session"""
#         return SessionLocal()


#     def _get_chat_history(self, module_id: str, workflow: str) -> List[Dict[str, Any]]:
#         """Get chat history for a specific module and workflow"""
#         try:
#             with self._get_db() as db:
#                 # Query using SQLAlchemy
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

#                     # Add tool-specific data if present
#                     if msg.message_type in ["tool_call", "tool_result"]:
#                         if msg.message_type == "tool_call":
#                             message["tool_calls"] = msg.tool_data
#                         else:
#                             message["tool_results"] = msg.tool_data

#                     history.append(message)
#                 return history
#         except Exception as e:
#             raise AgentError(f"Failed to get chat history: {str(e)}")

#     def _add_to_history(
#         self,
#         module_id: str,
#         workflow: str,
#         role: str,
#         content: str,
#         message_type: str = "text",
#         tool_data: Optional[Dict[str, Any]] = None
#     ):
#         """Add message to chat history with support for tool calls and results"""
#         if not content:
#             content = "Empty message"  # Ensure we never have null content

#         try:
#             with self._get_db() as db:
#                 chat_message = ChatHistory(
#                     module_id=module_id,
#                     section=workflow,
#                     role=role,
#                     content=content,
#                     timestamp=datetime.now(UTC),
#                     message_type=message_type,
#                     tool_data=tool_data
#                 )
#                 db.add(chat_message)
#                 db.commit()

#         except Exception as e:
#             raise AgentError(f"Failed to add message to history: {str(e)}")



#     async def _handle_edit_workflow(self, module_id: str, user_input: str) -> Dict[str, Any]:
#         """Handle edit workflow by forwarding to CoderService"""
#         try:
#             self.stage_state_service.set_executing(module_id)

#             # Get module metadata to get repo name
#             module_metadata = self.module_service.get_module_metadata(module_id)
            
#             # Get repository path
#             repo_path = self.repo_service._get_repo_path(module_metadata.repo_name)
            
#             # Initialize CoderService
#             coder_service = CoderService(str(repo_path), self.model_service)
            
#             # Forward request to CoderService
#             result = await coder_service.process_request(module_id,Context(user_input, Role.USER))

#             self.stage_state_service.set_standby(module_id)
            
#             return {
#                 "response": result["message"],
#                 "results": []  # CoderService doesn't return tool results
#             }
            
#         except Exception as e:
#             self.stage_state_service.set_standby(module_id)
#             raise AgentError(f"Failed to handle edit workflow: {str(e)}")






#     async def _get_combined_workflow_metadata(
#             self,
#             module_id: str,
#             workflow: str
#         ) -> Dict[str, Any]:
#             """Get combined workflow metadata from main and shared workflows"""
#             # Get main module's workflow metadata
#             main_workflow = self.workflow_service.get_workflow_metadata(
#                 module_id=module_id,
#                 workflow=workflow
#             )
            
#             try:
#                 # Get connected modules
#                 connected_modules = self.module_service.get_linked_modules(
#                     module_id=module_id,
#                     relation_type=RelationType.CONNECTION
#                 )
                
#                 logger.info(f"Found connected modules: {connected_modules}")
                
#                 combined_instructions = [main_workflow.get("instructions", "")]
#                 combined_actions = main_workflow.get("actions", [])
#                 combined_requirements = set(main_workflow.get("requirements", []))
                
#                 # Process each connected module
#                 for connected_module in connected_modules:
#                     try:
#                         logger.info(f"Processing share workflow from module: {connected_module.module_id}")
#                         share_workflow = self.workflow_service.get_workflow_metadata(
#                             module_id=connected_module.module_id,
#                             workflow="share"
#                         )
                        
#                         if share_workflow.get("instructions"):
#                             module_context = f"\nShared instructions from connected module {connected_module.module_name} ({connected_module.module_id}):\n"
#                             combined_instructions.extend([
#                                 module_context,
#                                 share_workflow["instructions"]
#                             ])
                        
#                         # Add shared actions with complete source information
#                         for action in share_workflow.get("actions", []):
#                             shared_action = {
#                                 **action,
#                                 "source_module_id": connected_module.module_id,
#                                 "source_module_name": connected_module.module_name,
#                                 "source_workflow": "share",  # Explicitly mark as share workflow
#                                 "name": action["name"],
#                                 "description": f"[Shared from {connected_module.module_name}] {action['description']}"
#                             }
#                             logger.info(f"Adding shared action: {shared_action}")
#                             combined_actions.append(shared_action)
                        
#                         combined_requirements.update(share_workflow.get("requirements", []))
                        
#                     except Exception as e:
#                         logger.warning(
#                             f"Failed to get share workflow from connected module {connected_module.module_id}: {str(e)}"
#                         )
#                         continue
                
#                 # Add source info to main module actions
#                 main_actions = []
#                 for action in combined_actions:
#                     if "source_module_id" not in action:
#                         action = {
#                             **action,
#                             "source_module_id": module_id,
#                             "source_workflow": workflow,
#                         }
#                     main_actions.append(action)
                
#                 return {
#                     "instructions": "\n".join(filter(None, combined_instructions)),
#                     "actions": main_actions,
#                     "requirements": list(combined_requirements)
#                 }
                
#             except Exception as e:
#                 logger.warning(f"Failed to process connected modules: {str(e)}")
#                 return main_workflow

#     async def execute_agent_workflow(
#         self,
#         module_id: str,
#         workflow: str,
#         user_input: str
#     ) -> Dict[str, Any]:
#         """Execute workflow with state management and error handling."""
#         # Check current status
#         current_stage, current_state = self.stage_state_service.get_status(module_id)
        
#         if workflow not in valid_workflows[current_stage]:
#             raise AgentError(
#                 f"Cannot execute '{workflow}' workflow in {current_stage.value} stage. "
#                 f"Only '{str(valid_workflows[current_stage])}' workflows are allowed."
#             )
        
#         if current_state == AgentState.EXECUTING:
#             raise AgentError("Agent is currently executing another workflow")
        
#         if workflow == "edit":
#             return await self._handle_edit_workflow(module_id, user_input)
        
#         self.stage_state_service.set_executing(module_id)
        
#         try:
#             # Get combined workflow metadata including connected modules
#             workflow_data = await self._get_combined_workflow_metadata(
#                 module_id=module_id,
#                 workflow=workflow
#             )
            
#             # Get chat history and prepare messages
#             messages = self._get_combined_stage_history(module_id, current_stage, workflow)
#             messages = self._add_instruction_prompts(messages, workflow_data)
            
#             if workflow_data.get("instructions"):
#                 if not any(msg["role"] == "system" for msg in messages):
#                     messages.insert(0, {
#                         "role": "system",
#                         "content": workflow_data["instructions"]
#                     })
            
#             # Convert steps to tools with proper parameters
#             tools, action_map = self._convert_steps_to_tools(
#                 module_id=module_id,
#                 workflow=workflow,
#                 steps=workflow_data["actions"]  # Pass the actions from workflow_data
#             )
            
#             # Add stage-specific tools
#             if current_stage == AgentStage.INITIALIZE:
#                 tools.append(PROMOTE_TOOL_SCHEMA)
#             elif current_stage == AgentStage.MAINTAIN:
#                 tools.append(PROMOTE_TOOL_SCHEMA)
            
#             # Process the workflow with both tools and action map
#             result = await self._process_workflow(
#                 module_id=module_id,
#                 workflow=workflow,
#                 user_input=user_input,
#                 messages=messages,
#                 tools=tools,
#                 tool_to_action_map=action_map
#             )
            
#             self.stage_state_service.set_standby(module_id)
#             return result
            
#         except Exception as e:
#             self.stage_state_service.set_standby(module_id)
#             raise AgentError(f"Failed to execute workflow: {str(e)}")





#     def _get_combined_stage_history(
#         self,
#         module_id: str,
#         current_stage: AgentStage,
#         current_workflow: str
#     ) -> List[Dict[str, str]]:
#         """
#         Get combined chat history from current and previous stages.
        
#         Args:
#             module_id: Module ID
#             current_stage: Current stage of the module
#             current_workflow: Current workflow being executed
            
#         Returns:
#             Combined list of chat messages from relevant stages
#         """
#         combined_history = []

        
#         # Calculate previous stages based on valid_workflows
#         all_stages = list(valid_workflows.keys())
#         current_stage_index = all_stages.index(current_stage)
#         previous_stages = []
        
#         # Collect all workflows from previous stages
#         for stage in all_stages[:current_stage_index]:
#             previous_stages.extend(valid_workflows[stage])
        
#         # Get histories from previous stages
#         for prev_workflow in previous_stages:
#             stage_history = self._get_chat_history(module_id, prev_workflow)
#             if stage_history:
#                 combined_history.extend(stage_history)
        
#         # Add current stage history
#         current_history = self._get_chat_history(module_id, current_workflow)
#         if current_history:
#             combined_history.extend(current_history)
        
#         return combined_history






#     async def _process_workflow(
#         self,
#         module_id: str,
#         workflow: str,
#         user_input: str,
#         messages: List[Dict[str, str]],
#         tools: List[Dict[str, Any]],
#         tool_to_action_map: Dict[str, ActionInfo]  # Add action map parameter
#     ) -> Dict[str, Any]:
#         """Process workflow execution with tools"""
#         logger.info("Processing workflow...")
        
#         messages.append({"role": "user", "content": user_input})
#         self._add_to_history(module_id, workflow, "user", user_input)

#         response = await self.model_service.chat_completion(
#             messages=messages,
#             tools=tools,
#             tool_choice="auto"
#         )

#         assistant_message = response.choices[0].message
        
#         if assistant_message.content:
#             self._add_to_history(
#                 module_id,
#                 workflow,
#                 "assistant",
#                 assistant_message.content
#             )

#         results = []

#         if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
#             tool_results_summary = []

#             for tool_call in assistant_message.tool_calls:
#                 if tool_call.function.name == "promote_stage":
#                     # Handle stage promotion
#                     args = json.loads(tool_call.function.arguments)
#                     target_stage = AgentStage[args["target_stage"]]
#                     self.stage_state_service.promote_stage(module_id, target_stage)
#                     result = {
#                         "status": "success",
#                         "message": f"Promoted to {target_stage.value} stage"
#                     }
#                     results.append({
#                         "step": "promote_stage",
#                         "result": result
#                     })
#                     tool_results_summary.append(
#                         f"Stage promoted to {target_stage.value}"
#                     )
#                 else:
#                     # Get action info from map
#                     action_info = tool_to_action_map.get(tool_call.function.name)
#                     if not action_info:
#                         raise AgentError(f"Unknown tool name: {tool_call.function.name}")

#                     # Execute the tool with full action info
#                     result = self.workflow_service.execute_workflow_step(
#                         module_id=module_id,
#                         workflow=workflow,
#                         action_info=action_info,
#                         parameters=json.loads(tool_call.function.arguments)
#                     )

#                     logger.info(f"Tool call '{action_info.name}' executed with result: {result}")
#                     results.append({
#                         "action": action_info.name,
#                         "result": result
#                     })

#                     tool_results_summary.append(
#                         f"Action '{action_info.name}' executed with result: {json.dumps(result)}"
#                     )

#             tool_results_message = (
#                 "Here are the results of the operations you requested:\n\n" +
#                 "\n".join(tool_results_summary)
#             )

#             self._add_to_history(
#                 module_id,
#                 workflow,
#                 "user",
#                 tool_results_message,
#                 message_type="tool_result",
#                 tool_data=results
#             )

#             updated_messages = self._get_chat_history(module_id, workflow)

#             final_response = await self.model_service.chat_completion(
#                 messages=updated_messages,
#                 tools=None
#             )

#             final_message = final_response.choices[0].message
#             if final_message and hasattr(final_message, 'content') and final_message.content:
#                 self._add_to_history(
#                     module_id,
#                     workflow,
#                     "assistant",
#                     final_message.content
#                 )

#             return {
#                 "response": final_message.content if final_message.content else "",
#                 "results": results
#             }
        
#         return {
#             "response": assistant_message.content if assistant_message.content else "",
#             "results": results
#         }

    


#     def _convert_steps_to_tools(
#             self,
#             module_id: str,
#             workflow: str,
#             steps: List[Dict[str, Any]]
#         ) -> Tuple[List[Dict[str, Any]], Dict[str, ActionInfo]]:
#             """Convert workflow steps to tools format with action mapping."""
#             tools = []
#             tool_to_action_map = {}

#             for step in steps:
#                 metadata = step.get("metadata", None)
#                 if metadata is None:
#                     continue

#                 logger.info(f"Converting step to tool: {step}")

#                 # Get source information from the step
#                 source_module_id = step.get("source_module_id", module_id)
#                 source_workflow = step.get("source_workflow", workflow)
#                 source_module_name = step.get("source_module_name")

#                 # Create action info with correct source information
#                 action_info = ActionInfo(
#                     module_id=source_module_id,
#                     workflow=source_workflow,  # This will be 'share' for shared actions
#                     action_path=step.get("action", ""),
#                     name=step.get("name", ""),
#                     description=step.get("description", "") or metadata.description,
#                     source_module_name=source_module_name
#                 )

#                 logger.info(f"Created action info: {action_info}")

#                 tool = {
#                     "type": "function",
#                     "function": {
#                         "name": action_info.name,
#                         "description": action_info.description,
#                         "parameters": metadata.parameters
#                     }
#                 }
#                 tools.append(tool)
#                 tool_to_action_map[action_info.name] = action_info

#             return tools, tool_to_action_map




#     def get_workflow_history(self, module_id: str, workflow: str) -> List[Dict[str, str]]:
#         """
#         Retrieve chat history for a specific section of a module
        
#         Args:
#             module_id: Module ID
#             workflow: Workflow name
            
#         Returns:
#             List of chat messages with role, content, and timestamp
#         """
#         try:
#             return self._get_chat_history(module_id, workflow)
#         except Exception as e:
#             raise AgentError(f"Failed to retrieve workflow history: {str(e)}")





#     def get_module_status(self, module_id: str) -> Dict[str, str]:
#         """
#         Get current stage and state for a module
        
#         Args:
#             module_id: Module ID to check
            
#         Returns:
#             Dict containing stage, state and last_updated timestamp
#         """
#         try:
#             stage, state = self.stage_state_service.get_status(module_id)
#             last_updated = self.stage_state_service.get_last_updated(module_id)

#             return {
#                 "stage": stage.value,
#                 "state": state.value,
#                 "last_updated": last_updated
#             }
#         except Exception as e:
#             raise AgentError(f"Failed to get module status: {str(e)}")



#     def _add_instruction_prompts(self, messages: List[Dict[str, str]], workflow_data: Dict[str, Any]) -> List[Dict[str, str]]:
#         """
#         Add instruction prompts to messages list.
#         Only adds to current messages, doesn't save to history.
#         """
#         instructions = []
        
#         # Add global instructions about tool execution
#         base_instructions = """
#         When handling user requests:
        
#         1. For tool executions:
#         - Explain your plan before executing tools
#         - Execute tools one at a time
#         - After each tool:
#             - Explain the results
#             - If more tools are needed, explain what you'll do next
#         - Use previous results to inform next actions
        
#         2. Tool execution guidelines:
#         - Execute sequentially when:
#             - Results from one tool affect another
#             - Actions need specific order
#         - Only use parallel execution for independent actions
        
#         3. Communication:
#         - Keep user informed of actions
#         - Explain reasoning for tool choices
#         - Provide clear result summaries
#         """
#         instructions.append(base_instructions)
        
#         # Add workflow-specific instructions if available
#         if workflow_data.get("instructions"):
#             instructions.append(workflow_data["instructions"])
            
#         # Combine all instructions
#         if instructions:
#             combined_instructions = "\n\n".join(instructions)


#             # logger.info("Combined instructions:", str(combined_instructions))
            
#             # Update messages list
#             if not any(msg["role"] == "system" for msg in messages):
#                 messages.insert(0, {
#                     "role": "system",
#                     "content": combined_instructions
#                 })
#             else:
#                 # Update existing system message
#                 for msg in messages:
#                     if msg["role"] == "system":
#                         msg["content"] = f"{msg['content']}\n\n{combined_instructions}"
#                         break
                        
#         return messages