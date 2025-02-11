from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import importlib.util
import inspect
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.config.workflow_config import WorkflowConfigService

from engine.db.models import ChatHistory
from engine.db.session import SessionLocal
from engine.services.execution.model import ModelService
from engine.services.execution.state import StateService, AgentState
from engine.services.core.module import ModuleService, RelationType
from engine.services.execution.workflow import (
    ActionInfo,
    WorkflowService,
    WorkflowMetadataResult,
    WorkflowActionMetadata
)
from engine.services.storage.repository import RepoService
from engine.utils.logging import logger
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
        workflow: str,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for a module and workflow session
        
        Args:
            module_id: Module ID
            workflow: Workflow type
            session_id: Optional session ID. If not provided, returns default session (all zeros UUID)
        """
        try:
            with self._db as db:
                stmt = (
                    select(ChatHistory)
                    .where(
                        ChatHistory.module_id == module_id,
                        ChatHistory.section == workflow,
                        ChatHistory.session_id == (session_id or str(uuid.UUID(int=0)))
                    )
                    .order_by(ChatHistory.timestamp.asc())
                )
                messages = db.execute(stmt).scalars().all()

                history = []
                for msg in messages:
                    message = {
                        "role": msg.role,
                        "content": msg.content
                    }
                    if msg.message_type in ["tool_call", "tool_result"]:
                        if msg.message_type == "tool_call":
                            message["tool_calls"] = msg.tool_data
                        else:
                            message["tool_results"] = msg.tool_data
                    history.append(message)
                return history
        except Exception as e:
            raise AgentError(f"Failed to get chat history: {str(e)}")

    def add_to_history(
        self,
        module_id: str,
        workflow: str,
        role: str,
        content: str,
        message_type: str = "text",
        tool_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ):
        """
        Add message to chat history
        
        Args:
            module_id: Module ID
            workflow: Workflow type
            role: Message role (user/assistant)
            content: Message content
            message_type: Message type (text/tool_call/tool_result)
            tool_data: Optional tool data
            session_id: Optional session ID. If not provided, uses default session (all zeros UUID)
        """
        try:
            with self._db as db:
                chat_message = ChatHistory(
                    module_id=module_id,
                    section=workflow,
                    role=role,
                    content=content or "Empty message",
                    timestamp=datetime.now(UTC),
                    message_type=message_type,
                    tool_data=tool_data,
                    session_id=session_id or str(uuid.UUID(int=0))
                )
                db.add(chat_message)
                db.commit()
        except Exception as e:
            raise AgentError(f"Failed to add to history: {str(e)}")
