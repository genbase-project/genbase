from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import importlib.util
import inspect
import json
import uuid
from litellm import ChatCompletionMessageToolCall
from sqlalchemy import JSON, select

from engine.db.models import ChatHistory
from engine.db.session import SessionLocal
from engine.services.execution.model import ModelService
from engine.services.execution.state import StateService, AgentState
from engine.services.core.module import ModuleService
from engine.services.storage.workspace import WorkspaceService
from loguru import logger
from pathlib import Path


class AgentError(Exception):
    """Base exception for agent operations"""
    pass

class ChatHistoryManager:
    """Manages chat history operations"""
    
    def __init__(self):
        self._db = SessionLocal()
    
    def get_chat_history(
        self,
        module_id: str,
        profile: str,
        session_id: Optional[str] = None,
        return_json: bool = False

    ) -> List[Dict[str, Any]]:
        """
        Get chat history for a module and profile session
        
        Args:
            module_id: Module ID
            profile: Profile type
            session_id: Optional session ID. If not provided, returns default session (all zeros UUID)
        """
        try:
            with self._db as db:
                stmt = (
                    select(ChatHistory)
                    .where(
                        ChatHistory.module_id == module_id,
                        ChatHistory.profile == profile,
                        ChatHistory.session_id == (session_id or str(uuid.UUID(int=0)))
                    )
                    .order_by(ChatHistory.timestamp.asc())
                )
                messages = db.execute(stmt).scalars().all()

                history = [self._format_message(msg, return_json) for msg in messages]
                return history
        except Exception as e:
            raise AgentError(f"Failed to get chat history: {str(e)}")

    def add_to_history(
        self,
        module_id: str,
        profile: str, 
        role: str,
        content: str,
        message_type: str = "text",
        tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None,
        session_id: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,

    ):
        """
        Add message to chat history
        W
        Args:
            module_id: Module ID
            profile: Profile type
            role: Message role (user/assistant)
            content: Message content
            message_type: Message type (text/tool_call/tool_result)
            tool_data: Optional tool data
            session_id: Optional session ID. If not provided, uses default session (all zeros UUID)
        """
        try:
            with self._db as db:
                logger.debug(f"tool_calls: {tool_calls}")
                chat_message = ChatHistory(
                    module_id=module_id,
                    profile=profile,
                    role=role,
                    content=content,
                    timestamp=datetime.now(UTC),
                    message_type=message_type,
                    tool_calls=[tool_call.model_dump_json() for tool_call in tool_calls] if tool_calls else None,
                    session_id=session_id or str(uuid.UUID(int=0)),
                    tool_call_id=tool_call_id,
                    name=name
                )
                db.add(chat_message)
                db.commit()
        except Exception as e:
            raise AgentError(f"Failed to add to history: {str(e)}")

    def _format_message(self, msg: ChatHistory, return_json: bool = False) -> Dict[str, Any]:
        """
        Format a ChatHistory message into a dictionary
        
        Args:
            msg: ChatHistory model instance
            return_json: Whether to return tool calls as JSON (True) or model instances (False)
            
        Returns:
            Formatted message dictionary
        """
        message = {
            "role": msg.role,
            "content": msg.content
        }
        
        if msg.tool_call_id:
            message["tool_call_id"] = msg.tool_call_id

        if msg.tool_calls:
            if return_json:
                message["tool_calls"] = [
                    json.loads(tool_call_json)
                    for tool_call_json in msg.tool_calls
                ]
            else:
                message["tool_calls"] = [
                    ChatCompletionMessageToolCall.model_validate_json(tool_call_json)
                    for tool_call_json in msg.tool_calls
                ]

        if msg.name:
            message["name"] = msg.name
            
        return message

    def get_last_message(
        self,
        module_id: str,
        profile: str,
        session_id: Optional[str] = None,
        return_json: bool = False,
        role: str = "assistant"
    ) -> Optional[Dict[str, Any]]:
        """
        Get the last message from the assistant in chat history
        
        Args:
            module_id: Module ID
            profile: Profile type
            session_id: Optional session ID. If not provided, uses default session (all zeros UUID)
            return_json: Whether to return tool calls as JSON
            
        Returns:
            Last assistant message as a dictionary, or None if no assistant messages found
        """
        try:
            with self._db as db:
                stmt = (
                    select(ChatHistory)
                    .where(
                        ChatHistory.module_id == module_id,
                        ChatHistory.profile == profile,
                        ChatHistory.session_id == (session_id or str(uuid.UUID(int=0))),
                        ChatHistory.role == role
                    )
                    .order_by(ChatHistory.timestamp.desc())
                    .limit(1)
                )
                
                message = db.execute(stmt).scalar_one_or_none()
                return self._format_message(message, return_json) if message else None
                
        except Exception as e:
            raise AgentError(f"Failed to get last assistant message: {str(e)}")
