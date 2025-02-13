import asyncio
import uuid
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

import pytest
from engine.services.agents.base_agent import BaseAgent, AgentContext, AgentServices
from engine.services.execution.action import FunctionMetadata
from engine.services.execution.workflow import WorkflowExecutionResult

class TestAgent(BaseAgent):
    """Test implementation of NextBaseAgent"""
    
    @property
    def agent_type(self) -> str:
        return "test_agent"
        
    async def process_workflow(self, context: AgentContext, workflow_data: Any) -> Dict[str, Any]:
        return {"status": "success"}

def create_mock_services():
    return AgentServices(
        model_service=Mock(),
        workflow_service=AsyncMock(),
        module_service=Mock()
    )

@pytest.mark.asyncio
async def test_chat_history():
    # Create test agent
    agent = TestAgent(create_mock_services())
    
    # Generate unique IDs
    module_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    # Set context
    agent.context = AgentContext(
        module_id=module_id,
        workflow="test_workflow",
        user_input="test input",
        session_id=session_id
    )
    
    # Test adding regular message
    agent.add_to_history("user", "Hello!")
    
    # Test function tool
    function_metadata = {
        "name": "get_weather",
        "description": "Get weather for location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["location"]
        }
    }
    
    # Add function call
    agent.add_to_history(
        role="assistant",
        content="Checking weather...",
        message_type="tool_call",
        tools_info=[{
            "type": "function",
            "data": FunctionMetadata(**function_metadata)
        }]
    )
    
    # Add function result
    agent.add_to_history(
        role="tool",
        content="Weather retrieved",
        message_type="tool_result", 
        tools_info=[{
            "type": "workflow",
            "data": WorkflowExecutionResult(
                status="success",
                message="Got weather",
                result={"temperature": 72, "conditions": "sunny"}
            )
        }]
    )
    
    # Get history
    history = agent.get_chat_history()
    
    # Verify all messages are present
    assert len(history) == 3
    
    # Verify regular message
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello!"
    assert history[0]["message_type"] == "text"
    
    # Verify function call
    assert history[1]["role"] == "assistant"
    assert history[1]["message_type"] == "tool_call"
    tool_data = history[1]["tool_data"]
    assert len(tool_data) == 1
    assert tool_data[0]["type"] == "function"
    assert tool_data[0]["function"]["name"] == "get_weather"
    
    # Verify function result
    assert history[2]["role"] == "tool" 
    assert history[2]["message_type"] == "tool_result"
    result_data = history[2]["tool_data"]
    assert len(result_data) == 1
    assert result_data[0]["type"] == "workflow"
    assert result_data[0]["status"] == "success"
    assert result_data[0]["result"]["temperature"] == 72

if __name__ == "__main__":
    asyncio.run(test_chat_history())
