from typing import Dict, List, Any
import json
from engine.services.agents.base_agent import BaseAgent, AgentContext
from engine.services.execution.workflow import WorkflowMetadataResult
from engine.utils.logging import logger

TASKER_INSTRUCTIONS = """You are a task execution agent responsible for managing workflow operations.

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
- Handle errors and retries"""

class TaskerAgent(BaseAgent):
    """Agent for handling task-based workflows"""

    @property
    def agent_type(self) -> str:
        return "tasker"

    async def process_workflow(
        self,
        context: AgentContext,
        workflow_data: WorkflowMetadataResult
    ) -> Dict[str, Any]:
        """Process a workflow request"""
        try:
            # Build initial context with workflow-specific instructions
            instructions = TASKER_INSTRUCTIONS

            # Add workflow-specific instructions if available
            if workflow_data.instructions:
                instructions += f"\n\n##Workflow Instructions:\n{workflow_data.instructions}"

            # Build context with combined instructions
            system_prompt, _ = await self.build_context(
                agent_instructions=instructions,
                required_xml_elements=["user_prompt"]
            )

            # Initial response based on user input
            response = await self.chat_completion(
                messages=[{"role": "user", "content": context.user_input}]
            )

            assistant_message = response.choices[0].message
            results = []

            # Handle assistant message
            if assistant_message.content:
                self.add_to_history(
                    role="assistant",
                    content=assistant_message.content
                )

            # Process tool calls if any
            if hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls:
                tool_responses = []

                for tool_call in assistant_message.tool_calls:
                    try:
                        # Parse parameters
                        parameters = json.loads(tool_call.function.arguments)

                        # Execute the workflow action
                        result = await self.execute_workflow_action(
                            tool_call.function.name,
                            parameters
                        )

                        # Format successful result
                        result_entry = {
                            "action": tool_call.function.name,
                            "result": result
                        }
                        results.append(result_entry)
                        
                        # Add result message entry for LLM context
                        tool_responses.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_call.function.name,
                            "content": json.dumps(result)
                        })

                        # Add to history with tool call ID
                        self.add_to_history(
                            role="tool",
                            content=json.dumps(result),
                            message_type="tool_result",
                            tool_call_id=tool_call.id,
                            tool_name=tool_call.function.name,
                            tools_info=[{
                                "type": "function",
                                "data": result_entry
                            }]
                        )

                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error executing tool {tool_call.function.name}: {error_msg}")
                        
                        # Format error result
                        error_result = {
                            "action": tool_call.function.name,
                            "error": error_msg
                        }
                        results.append(error_result)

                        # Add error message entry for LLM context
                        tool_responses.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_call.function.name,
                            "content": json.dumps({"error": error_msg})
                        })

                        # Add error to history
                        self.add_to_history(
                            role="tool",
                            content=json.dumps({"error": error_msg}),
                            message_type="error",
                            tool_call_id=tool_call.id,
                            tool_name=tool_call.function.name,
                            tools_info=[{
                                "type": "function",
                                "data": error_result
                            }]
                        )

                # Get final response after tool executions
                final_response = await self.chat_completion(
                    messages=[{
                        "role": "assistant",
                        "content": None,
                        "tool_calls": assistant_message.tool_calls
                    }] + tool_responses + [
                        {"role": "user", "content": "What should I do next based on the tool results?"}
                    ]
                )

                final_message = final_response.choices[0].message
                if final_message.content:
                    self.add_to_history(
                        role="assistant",
                        content=final_message.content
                    )

            return {
                "response": assistant_message.content if assistant_message.content else "",
                "results": results
            }

        except Exception as e:
            logger.error(f"Error in process_workflow: {str(e)}")
            raise
