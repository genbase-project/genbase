from typing import Dict, List, Any
import json
from engine.config.workflow_config import WorkflowConfigurations
from engine.services.agents.base_agent import Action, AgentContext, AgentError, BaseAgent
from engine.utils.logging import logger
from engine.services.execution.stage_state import COMPLETE_WORKFLOW_SCHEMA
from engine.services.execution.workflow import ActionInfo
from dataclasses import asdict

class TaskerAgent(BaseAgent):
    """Agent for handling task-based workflows"""

    @property
    def agent_type(self) -> str:
        return WorkflowConfigurations.TASKER_AGENT

    @property
    def default_actions(self) -> List[Action]:
        """Return agent-specific default actions"""
        logger.debug("Getting default actions for TaskerAgent")
        return [
            Action(
                name="complete_workflow",
                description="Mark a workflow as completed",
                schema=COMPLETE_WORKFLOW_SCHEMA,
                function=self.services.stage_state_service.complete_workflow
            )
        ]

    def _get_base_instructions(self) -> str:
        return """You are a task execution agent responsible for managing module operations.

When handling user requests:

1. For tool executions:
- Explain your plan before executing tools
- Execute tools one at a time
- After each tool:
    - Explain the results
    - If more tools are needed, explain what you'll do next
- Use previous results to inform next actions

2. Tool execution guidelines:
- Execute sequentially when:
    - Results from one tool affect another
    - Actions need specific order
- Only use parallel execution for independent actions

3. Communication:
- Keep user informed of actions
- Explain reasoning for tool choices
- Provide clear result summaries

4. Workflow Completion:
- Mark workflows as completed when all requirements are met
- Verify successful completion of all tasks
- Explain completion decisions

If asked what you can do, explain your capabilities based on the available tools and actions."""

    def _serialize_metadata(self, obj: Any) -> Any:
        """Serialize objects that aren't JSON serializable"""
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

    def _safe_json_dump(self, obj: Any) -> str:
        """Safely dump object to JSON string"""
        try:
            return json.dumps(obj, default=self._serialize_metadata, indent=2)
        except Exception as e:
            logger.warning(f"Error serializing object: {e}")
            return str(obj)

    async def _process_workflow(
        self,
        context: AgentContext,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process workflow execution with tools"""
        try:
            logger.info(f"Processing workflow for module {context.module_id}, workflow {context.workflow}")
            
            # Get workflow metadata
            workflow_data = await self.get_combined_workflow_metadata(context)
            
            # Add instruction prompts
            messages = self._add_instruction_prompts(messages, workflow_data, context)
            
            # Get all workflow actions including defaults
            all_workflow_actions = workflow_data.get("actions", [])
            
            # Get workflow-specific default actions
            workflow_default_actions = self.get_workflow_default_actions(context.workflow)
            for action in workflow_default_actions:
                all_workflow_actions.append({
                    "name": action.name,
                    "description": action.description,
                    "action": action.name,
                    "metadata": action.schema["function"]
                })
            
            # Get action tools and mapping
            workflow_tools, action_map = await self.get_workflow_actions(
                context, 
                all_workflow_actions
            )
            
            # Get agent default actions
            agent_actions = self.default_actions
            
            # Combine workflow tools with agent default tools
            all_tools = workflow_tools + [action.schema for action in agent_actions]

            # Add user input to messages
            messages.append({"role": "user", "content": context.user_input})
            
            # Get model response
            response = await self.services.model_service.chat_completion(
                messages=messages,
                tools=all_tools if all_tools else None,
                tool_choice="auto" if all_tools else None
            )
            
            assistant_message = response.choices[0].message
            results = []
            
            # Handle assistant message
            if assistant_message.content:
                self.history_manager.add_to_history(
                    context.module_id,
                    context.workflow,
                    "assistant",
                    assistant_message.content
                )
            
            # Handle tool calls
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                tool_results_summary = []
                
                for tool_call in assistant_message.tool_calls:
                    try:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        
                        # Check different types of actions
                        workflow_default = next(
                            (action for action in workflow_default_actions if action.name == tool_name),
                            None
                        )
                        agent_default = next(
                            (action for action in agent_actions if action.name == tool_name),
                            None
                        )
                        
                        if workflow_default:
                            # Execute workflow default action
                            result = workflow_default.function(
                                module_id=context.module_id,
                                **tool_args
                            )
                        elif agent_default:
                            # Execute agent default action
                            result = agent_default.function(
                                module_id=context.module_id,
                                **tool_args
                            )
                        else:
                            # Execute regular workflow action
                            action_info = action_map.get(tool_name)
                            if not action_info:
                                raise AgentError(f"Unknown tool: {tool_name}")
                            
                            result = self.services.workflow_service.execute_workflow_step(
                                module_id=context.module_id,
                                workflow=context.workflow,
                                action_info=action_info,
                                parameters=tool_args
                            )
                        
                        results.append({
                            "action": tool_name,
                            "result": result
                        })
                        
                        tool_results_summary.append(
                            f"Action '{tool_name}' executed with result: {json.dumps(result)}"
                        )
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error executing tool {tool_call.function.name}: {error_msg}")
                        results.append({
                            "action": tool_call.function.name,
                            "error": error_msg
                        })
                        tool_results_summary.append(f"Error executing '{tool_call.function.name}': {error_msg}")
                
                if tool_results_summary:
                    # Add tool results as user message
                    tool_results_message = (
                        "Here are the results of the operations you requested:\n\n" +
                        "\n".join(tool_results_summary)
                    )
                    
                    self.history_manager.add_to_history(
                        context.module_id,
                        context.workflow,
                        "user",
                        tool_results_message,
                        message_type="tool_result",
                        tool_data=results
                    )
                    
                    # Get fresh chat history for final response
                    updated_messages = self.history_manager.get_chat_history(
                        context.module_id,
                        context.workflow
                    )
                    
                    # Get final response
                    final_response = await self.services.model_service.chat_completion(
                        messages=updated_messages,
                        tools=None
                    )
                    
                    final_message = final_response.choices[0].message
                    if final_message.content:
                        self.history_manager.add_to_history(
                            context.module_id,
                            context.workflow,
                            "assistant",
                            final_message.content
                        )
                        return {
                            "response": final_message.content,
                            "results": results
                        }
            
            return {
                "response": assistant_message.content if assistant_message.content else "",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in _process_workflow: {str(e)}")
            raise AgentError(f"Failed to process workflow: {str(e)}")