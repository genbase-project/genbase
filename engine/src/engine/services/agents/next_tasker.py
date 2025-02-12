from typing import Any, Dict, List, Optional
from engine.services.execution.workflow import WorkflowMetadataResult
from engine.services.agents.next_agent import NextBaseAgent, AgentContext
from engine.utils.logging import logger

class NextTaskerAgent(NextBaseAgent):
    """Next generation task execution agent"""

    @property
    def agent_type(self) -> str:
        return "tasker"

    def _get_base_instructions(self) -> str:
        return ""  # Base instructions will be passed directly

    async def process_workflow(
        self,
        context: AgentContext,
        workflow_data: WorkflowMetadataResult,
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute workflow tasks with full context"""
        try:
            # Initialize chat completion with workflow tools
            response = await self.chat_completion(
                user_input=context.user_input,
                tools=tools
            )

            # Process model response
            while True:
                if response.get("tool_calls"):
                    for tool_call in response["tool_calls"]:
                        # Execute action from tool call
                        if tool_call["type"] == "function":
                            function = tool_call["function"]
                            
                            # Log action execution
                            logger.info(
                                f"Executing action: {function['name']} with params: {function['arguments']}"
                            )

                            try:
                                # Execute the action
                                result = await self.execute_workflow_action(
                                    action_name=function["name"],
                                    parameters=function["arguments"]
                                )

                                # Add result to chat history
                                self.add_to_history(
                                    role="assistant",
                                    content="",
                                    metadata={
                                        "tool_call_id": tool_call["id"],
                                        "name": function["name"],
                                        "result": result
                                    }
                                )

                            except Exception as e:
                                error_msg = f"Error executing {function['name']}: {str(e)}"
                                logger.error(error_msg)
                                
                                # Add error to chat history
                                self.add_to_history(
                                    role="assistant",
                                    content="",
                                    metadata={
                                        "tool_call_id": tool_call["id"],
                                        "name": function["name"],
                                        "error": error_msg
                                    }
                                )

                    # Get next step from model
                    response = await self.chat_completion(
                        user_input="", 
                        tools=tools
                    )
                else:
                    # No more tool calls, add final response
                    self.add_to_history(
                        role="assistant",
                        content=response.get("content", "")
                    )
                    break

            # Return complete chat history
            return {
                "type": "chat",
                "messages": self.get_chat_history()
            }

        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            raise

    async def execute_shared_workflow_action(
        self,
        module_id: str,
        action_name: str,
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a shared action from another module with proper error handling"""
        try:
            result = await self.execute_shared_action(
                module_id=module_id,
                action_name=action_name,
                parameters=parameters
            )
            return result
            
        except Exception as e:
            error_msg = f"Error executing shared action {action_name}: {str(e)}"
            logger.error(error_msg)
            raise
