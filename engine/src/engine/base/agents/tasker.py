from typing import Dict, List, Any, Tuple
import json
from engine.services.agents.base_agent import Action, AgentContext, AgentError, BaseAgent
from engine.services.execution.workflow import ActionInfo
from engine.utils.logging import logger

class TaskerAgent(BaseAgent):
    """Agent for handling task-based workflows"""

    @property
    def agent_type(self) -> str:
        return "tasker"

    @property
    def default_actions(self) -> List[Action]:
        """Return agent-specific default actions"""
        logger.debug("Getting default actions for TaskerAgent")
        return []

    def _get_base_instructions(self) -> str:
        return """You are a task execution agent responsible for managing workflow operations.

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
- When asking for user input, use XML prompts format

4. Task Management:
- Process and execute workflow tasks
- Handle tool dependencies and execution order
- Track task completion status
- Provide progress updates
- Handle errors and retries

XML User Prompts:
When asking the user a question or requiring confirmation, use the XML format like this:

<user_prompt>
<question>
Your question goes here
</question>
<options>
<option description="Description of what this option means">Option text</option>
</options>
</user_prompt>

If asked what you can do, explain your capabilities based on the available tools and actions."""

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
            workflow_metadata = await self.get_workflow_metadata(context)
            
            # Add instruction prompts
            messages = self._add_instruction_prompts(messages, workflow_metadata, context)
            
            # Get all workflow actions including defaults
            all_workflow_actions = list(workflow_metadata.actions)
            
            # Get workflow-specific default actions
            workflow_default_actions = self.get_workflow_default_actions(context.workflow, context.module_id)
            for action in workflow_default_actions:
                # Create a metadata object that matches the required schema
                metadata = {
                    **action.schema["function"],  # Existing function metadata
                    "is_async": False  # Default to non-async for workflow default actions
                }
                
                all_workflow_actions.append({
                    "name": action.name,
                    "description": action.description,
                    "action": action.name,
                    "metadata": metadata
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

            from engine.utils.xml_prompts import create_user_prompt

            # Check if this is a confirmation request
            if "proceed" in context.user_input.lower() or "continue" in context.user_input.lower():
                formatted_input = "Would you like to continue?"  # Simple confirmation prompt
            else:
                formatted_input = context.user_input

            # Add user input to messages
            messages.append({"role": "user", "content": formatted_input})
            
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
                    assistant_message.content,
                    session_id=context.session_id
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
                        
                        # Ensure result is JSON serializable
                        if hasattr(result, 'model_dump'):
                            result_dict = result.model_dump()
                        else:
                            result_dict = {"value": str(result)}
                        
                        results.append({
                            "action": tool_name,
                            "result": result_dict
                        })
                        
                        # Use the serialized result for the summary
                        tool_results_summary.append(
                            f"Action '{tool_name}' executed with result: {json.dumps(result_dict)}"
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

                    # Add confirmation prompt using XML format
                    tool_results_message += "\n\n" + create_user_prompt(
                        "Would you like to continue with the next steps?",
                        [
                            ("Yes", "Continue with the workflow"),
                            ("No", "Stop here"),
                            ("Show details", "View more information about the results")
                        ]
                    )
                    
                    # Add to history
                    self.history_manager.add_to_history(
                        context.module_id,
                        context.workflow,
                        "user",
                        tool_results_message,
                        message_type="tool_result",
                        tool_data=results,
                        session_id=context.session_id
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
                            final_message.content,
                            session_id=context.session_id
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
