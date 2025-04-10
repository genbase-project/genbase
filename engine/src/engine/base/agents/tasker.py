from typing import Dict, List, Any, Optional, Tuple
import json
from engine.services.agents.base_agent import BaseAgent, AgentContext, IncludeOptions
from engine.services.execution.profile import ProfileMetadataResult
from loguru import logger

TASKER_INSTRUCTIONS = """You are a task execution agent responsible for managing profile operations.

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
- Process and execute profiles tasks
- Handle tool dependencies and execution order
- Track task completion status
- Provide progress updates
- Handle errors and retries"""

class TaskerAgent(BaseAgent):
    """Agent for handling task-based profiles"""

    @property
    def agent_type(self) -> str:
        return "tasker"

    async def process_request(
        self,
        context: AgentContext,
        profile_data: ProfileMetadataResult
    ) -> Dict[str, Any]:
        """Process a request"""
        try:








            # Build initial context with profile-specific instructions
            instructions = TASKER_INSTRUCTIONS




            
            # Add profile-specific instructions if available
            if profile_data.instructions:
                instructions += f"\n\n##Agent Profile Instructions:\n"
                for instruction in profile_data.instructions:
                    instructions += f"- {instruction.name}\n"
                    if instruction.module_id != context.module_id and instruction.module_id is not None:
                        instructions += f"Module ID: {instruction.module_id}\n"
                    instructions += f"Description:  {instruction.description}\n"
                    instructions += f"Content: {instruction.content}\n\n"


            # Build context with combined instructions
            system_prompt, _ = await self.set_context(
                agent_instructions=instructions,
               include=IncludeOptions(
                   elements=[]
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
