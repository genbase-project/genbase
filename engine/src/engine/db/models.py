from datetime import datetime, UTC
import enum
import secrets
from typing import Any, Dict, List, Optional
import uuid

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import JSON, UUID, Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from .encryption_utils import EncryptedJSON


from engine.db.base import Base

class Base(DeclarativeBase):
    pass



# From chat_history table in agent.py
class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[str] = mapped_column(String, nullable=False)
    profile: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    message_type: Mapped[str] = mapped_column(String, nullable=False, default="text")
    tool_calls: Mapped[Optional[List]] = mapped_column(JSON, nullable=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, default=lambda: str(uuid.UUID(int=0)))
    tool_call_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('module_id', 'profile', 'timestamp', 'session_id'),
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
    env_vars: Mapped[Dict] = mapped_column(EncryptedJSON, nullable=False)
    workspace_name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Updated relationships with cascade
    project_mappings: Mapped[List["ProjectModuleMapping"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )
    # Add agent_status relationship with cascade
    agent_status: Mapped["AgentStatus"] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        uselist=False
    )

    profile_statuses: Mapped[List["ProfileStatus"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )
  
    profile_stores: Mapped[List["ProfileStore"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )
    vector_store_configs: Mapped[List["VectorStoreConfig"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )
        
    resources_provided: Mapped[List["ModuleProvide"]] = relationship(
        "ModuleProvide",
        foreign_keys="ModuleProvide.provider_id",
        back_populates="provider",
        cascade="all, delete-orphan"
    )

    resources_received: Mapped[List["ModuleProvide"]] = relationship(
        "ModuleProvide",
        foreign_keys="ModuleProvide.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )

    api_keys: Mapped[List["ModuleApiKey"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan"
    )





class ModuleApiKey(Base):
    """API keys for authenticating module access to the LLM gateway"""
    __tablename__ = "module_api_keys"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    module_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id', ondelete='CASCADE'), nullable=False)
    api_key: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationship with Module
    module = relationship("Module", back_populates="api_keys")
    
    @staticmethod
    def generate_key() -> str:
        """Generate a secure API key"""
        # Format: mk_[random string]
        return f"mk_{secrets.token_urlsafe(32)}"




class ProvideType(enum.Enum):
    """Types of resources a module can provide to another module"""
    WORKSPACE = "workspace"
    TOOL = "tool"
    
class ModuleProvide(Base):
    """Tracks which module provides what resources to which other modules"""
    __tablename__ = "module_provides"
    
    provider_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id', ondelete='CASCADE'), primary_key=True)
    receiver_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id', ondelete='CASCADE'), primary_key=True)
    resource_type: Mapped[ProvideType] = mapped_column(Enum(ProvideType), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
        onupdate=text('CURRENT_TIMESTAMP')
    )
    
    # Relationships with back_populates instead of backref
    provider: Mapped[Module] = relationship(
        "Module",
        foreign_keys=[provider_id],
        back_populates="resources_provided"
    )
    receiver: Mapped[Module] = relationship(
        "Module",
        foreign_keys=[receiver_id],
        back_populates="resources_received"
    )
    

class StoreType(enum.Enum):
    CHROMA = "chroma"
    PINECONE = "pinecone"
    QDRANT = "qdrant"
    WEAVIATE = "weaviate"
    PGVECTOR = "pgvector"
    ELASTICSEARCH = "elasticsearch"
    OPENSEARCH = "opensearch"

class VectorStoreConfig(Base):
    """Stores vector store configuration for modules"""
    __tablename__ = "vector_store_configs"
    
    module_id: Mapped[str] = mapped_column(String, ForeignKey('modules.module_id', ondelete='CASCADE'), primary_key=True)
    store_name: Mapped[str] = mapped_column(String, primary_key=True)
    store_type: Mapped[StoreType] = mapped_column(Enum(StoreType), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    config: Mapped[Dict] = mapped_column(JSON, nullable=True)  # For any additional configuration
    
    # Relationship
    module: Mapped["Module"] = relationship(back_populates="vector_store_configs")


class ProfileStore(Base):
    """Store for profile-specific data"""
    __tablename__ = "profile_stores"
    
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

    profile: Mapped[str] = mapped_column(String, nullable=False)
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
    module: Mapped["Module"] = relationship(back_populates="profile_stores")




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
    state: Mapped[str] = mapped_column(
        Enum('STANDBY', 'EXECUTING', name='agent_state'),
        nullable=False
    )
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Updated relationship with back_populates
    module: Mapped[Module] = relationship(back_populates="agent_status")



class ProfileStatus(Base):
    """Tracks completion status of profiles for a module"""
    __tablename__ = "profile_status"
    
    module_id: Mapped[str] = mapped_column(
        String, 
        ForeignKey('modules.module_id', ondelete='CASCADE'),
        primary_key=True
    )
    profile_type: Mapped[str] = mapped_column(String, primary_key=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationship
    module: Mapped["Module"] = relationship(back_populates="profile_statuses")








class GlobalConfig(Base):
    """Stores global configuration settings"""
    __tablename__ = "global_configs"
    
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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







class User(SQLAlchemyBaseUserTableUUID, Base):
    pass
