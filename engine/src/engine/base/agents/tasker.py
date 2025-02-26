from typing import Dict, List, Any, Optional, Tuple
import json
from engine.services.agents.base_agent import BaseAgent, AgentContext, IncludeOptions
from engine.services.execution.workflow import WorkflowMetadataResult
from loguru import logger

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

    async def process_request(
        self,
        context: AgentContext,
        workflow_data: WorkflowMetadataResult,
        responses: Optional[List[Tuple[str, str, str]]] = None
    ) -> Dict[str, Any]:
        """Process a workflow request"""
        try:

            # response processing
            if responses:
                for response in responses:
                    if response[0] == "code_change":
                        # code change response
                        pass
                    elif response[0] == "user_prompt":
                        # user prompt response
                        pass
                    else:
                        logger.warning(f"Unknown response type: {response[1]}")









            # Build initial context with workflow-specific instructions
            instructions = TASKER_INSTRUCTIONS





            # Add workflow-specific instructions if available
            if workflow_data.instructions:
                instructions += f"\n\n##Workflow Instructions:\n{workflow_data.instructions}"

            # Build context with combined instructions
            system_prompt, _ = await self.set_context(
                agent_instructions=instructions,
               include=IncludeOptions(
                   giml_elements=["select", "code_diff"]
               )
            )
            

            # Initial response based on user input
            response = await self.create(
                messages=[{"role": "user", "content": context.user_input}]
            )

            

            assistant_message = response.choices[0].message


            return {
                "response": assistant_message.content if assistant_message.content else "",
                "results": []
            }

        except Exception as e:
            logger.error(f"Error in process_request: {str(e)}")
            raise
