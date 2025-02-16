from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import JSON, UUID, Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


from engine.db.base import Base

class Base(DeclarativeBase):
    pass

class WorkManifest(Base):
    """Stores AI-generated work manifests explaining module state"""
    __tablename__ = "work_manifests"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id', ondelete='CASCADE'), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    
    # Relationship
    module: Mapped["Module"] = relationship(back_populates="manifests")


# From chat_history table in agent.py
class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[str] = mapped_column(String, nullable=False)
    workflow: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    message_type: Mapped[str] = mapped_column(String, nullable=False, default="text")
    tool_calls: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, default=lambda: str(uuid.UUID(int=0)))
    tool_call_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('module_id', 'workflow', 'timestamp', 'session_id'),
    )

# From modules, project_module_mappings, and module_relations tables in module.py
class Module(Base):
    __tablename__ = "modules"
    
    module_id: Mapped[str] = mapped_column(String, primary_key=True)
    module_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    kit_id: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    env_vars: Mapped[Dict] = mapped_column(JSON, nullable=False)
    repo_name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Updated relationships with cascade
    project_mappings: Mapped[List["ProjectModuleMapping"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )
    source_relations: Mapped[List["ModuleRelation"]] = relationship(
        back_populates="source_module",
        foreign_keys="ModuleRelation.source_id",
        cascade="all, delete-orphan"
    )
    target_relations: Mapped[List["ModuleRelation"]] = relationship(
        back_populates="target_module",
        foreign_keys="ModuleRelation.target_id",
        cascade="all, delete-orphan"
    )
    # Add agent_status relationship with cascade
    agent_status: Mapped["AgentStatus"] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        uselist=False
    )

    workflow_statuses: Mapped[List["WorkflowStatus"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )
    
    manifests: Mapped[List["WorkManifest"]] = relationship(
        back_populates="module", 
        cascade="all, delete-orphan"
    )
    workflow_stores: Mapped[List["WorkflowStore"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )



class WorkflowStore(Base):
    """Store for workflow-specific data"""
    __tablename__ = "workflow_stores"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    module_id: Mapped[str] = mapped_column(
        String, 
        ForeignKey('modules.module_id', ondelete='CASCADE'),  # This line is crucial
        nullable=False
    )

    workflow: Mapped[str] = mapped_column(String, nullable=False)
    collection: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[Dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=text('CURRENT_TIMESTAMP')
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP')
    )
    # Add relationship to Module
    module: Mapped["Module"] = relationship(back_populates="workflow_stores")

    __table_args__ = (
        Index('idx_workflow_store_lookup', 'module_id', 'workflow', 'collection'),
    )



class ProjectModuleMapping(Base):
    __tablename__ = "project_module_mappings"
    
    project_id: Mapped[str] = mapped_column(String, ForeignKey('projects.id'), primary_key=True)
    module_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id'), primary_key=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationships
    module: Mapped[Module] = relationship(back_populates="project_mappings")
    project: Mapped["Project"] = relationship(back_populates="module_mappings")

class ModuleRelation(Base):
    __tablename__ = "module_relations"
    
    source_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id'), primary_key=True)
    target_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id'), primary_key=True)
    relation_type: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Explicitly define primary key constraint
    __table_args__ = (
        PrimaryKeyConstraint('source_id', 'target_id', 'relation_type', name='module_relations_pkey'),
    )

    
    # Relationships
    source_module: Mapped[Module] = relationship(
        foreign_keys=[source_id],
        back_populates="source_relations"
    )
    target_module: Mapped[Module] = relationship(
        foreign_keys=[target_id],
        back_populates="target_relations"
    )

# From projects table in project.py
class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationships
    module_mappings: Mapped[List[ProjectModuleMapping]] = relationship(back_populates="project")

# From agent_status table in state.py
class AgentStatus(Base):
    __tablename__ = "agent_status"
    
    module_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id', ondelete='CASCADE'), primary_key=True)
    stage: Mapped[str] = mapped_column(
        Enum('INITIALIZE', 'MAINTAIN', 'REMOVE', name='agent_stage'),
        nullable=False
    )
    state: Mapped[str] = mapped_column(
        Enum('STANDBY', 'EXECUTING', name='agent_state'),
        nullable=False
    )
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Updated relationship with back_populates
    module: Mapped[Module] = relationship(back_populates="agent_status")



class WorkflowStatus(Base):
    """Tracks completion status of workflows for a module"""
    __tablename__ = "workflow_status"
    
    module_id: Mapped[str] = mapped_column(
        String, 
        ForeignKey('modules.module_id', ondelete='CASCADE'),
        primary_key=True
    )
    workflow_type: Mapped[str] = mapped_column(String, primary_key=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationship
    module: Mapped["Module"] = relationship(back_populates="workflow_statuses")





# Index for chat_history
Index('idx_module_workflow', ChatHistory.module_id, ChatHistory.workflow)
