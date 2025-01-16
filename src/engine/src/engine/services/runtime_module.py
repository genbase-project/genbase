from pathlib import Path
import zipfile
import networkx as nx
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import shutil
import uuid
import os
from dataclasses import dataclass
from enum import Enum
import io

from engine.services.repository import (
    RepoService, 
    CommitInfo,
    RepoNotFoundError,
    RepoExistsError,
    RepositoryError
)
from engine.utils.file import extract_zip

class RelationType(Enum):
    DEPENDENCY = "dependency"
    CONTEXT = "context"

class RuntimeModuleError(Exception):
    """Base exception for runtime module errors"""
    pass

@dataclass
class RuntimeModuleMetadata:
    """Runtime module metadata"""
    id: str
    module_id: str
    version: str
    created_at: str
    env_vars: Dict[str, str]
    repo_name: str

class RuntimeModuleService:
    """Service for managing runtime modules and their relationships"""
    
    def __init__(
        self,
        db_path: str,
        workspace_base: str,
        repo_service: RepoService
    ):
        """
        Initialize runtime module service
        
        Args:
            db_path: Path to SQLite database
            workspace_base: Base path for module workspaces
            repo_service: Repository service for managing git repos
        """
        self.db_path = db_path
        self.workspace_base = Path(workspace_base)
        self.repo_service = repo_service
        self._init_db()
        
    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runtime_modules (
                    id TEXT PRIMARY KEY,
                    module_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    env_vars TEXT NOT NULL,
                    repo_name TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS module_relations (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id),
                    FOREIGN KEY (source_id) REFERENCES runtime_modules(id),
                    FOREIGN KEY (target_id) REFERENCES runtime_modules(id)
                )
            """)
            
    def create_runtime_module(
        self,
        module_id: str,
        version: str,
        env_vars: Dict[str, str]
    ) -> RuntimeModuleMetadata:
        """
        Create new runtime module instance
        
        Args:
            module_id: Module identifier
            version: Module version
            env_vars: Environment variables
            
        Returns:
            RuntimeModuleMetadata: Created module metadata
        """
        runtime_id = str(uuid.uuid4())
        repo_name = f"runtime-{runtime_id}"
        created_at = datetime.utcnow().isoformat()
        
        try:
            # Get workspace path
            workspace_path = self.workspace_base / f"{module_id}/{version}/workspace"
            print(workspace_path)
            if not workspace_path.exists():
                raise RuntimeModuleError(f"Workspace not found for {module_id} v{version}")

            # Create in-memory zip of workspace
            memory_zip = io.BytesIO()
            with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(workspace_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(workspace_path)
                        zipf.write(file_path, arcname)
            
            memory_zip.seek(0)
            
            # Create repository using repo service
            self.repo_service.create_repository(
                repo_name=repo_name,
                content_file=memory_zip,
                filename="workspace.zip",
                extract_func=extract_zip
            )
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO runtime_modules 
                    (id, module_id, version, created_at, env_vars, repo_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        runtime_id,
                        module_id,
                        version,
                        created_at,
                        str(env_vars),
                        repo_name
                    )
                )
            
            return RuntimeModuleMetadata(
                id=runtime_id,
                module_id=module_id,
                version=version,
                created_at=created_at,
                env_vars=env_vars,
                repo_name=repo_name
            )
            
        except Exception as e:
            # Cleanup on failure
            try:
                self.repo_service.delete_repository(repo_name)
            except:
                pass
            raise RuntimeModuleError(f"Failed to create runtime module: {str(e)}")
    
    def delete_runtime_module(self, runtime_id: str):
        """Delete runtime module"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get repo name
                cursor = conn.execute(
                    "SELECT repo_name FROM runtime_modules WHERE id = ?",
                    (runtime_id,)
                )
                result = cursor.fetchone()
                if not result:
                    return
                
                repo_name = result[0]
                
                # Delete relationships
                conn.execute(
                    "DELETE FROM module_relations WHERE source_id = ? OR target_id = ?",
                    (runtime_id, runtime_id)
                )
                
                # Delete module
                conn.execute(
                    "DELETE FROM runtime_modules WHERE id = ?",
                    (runtime_id,)
                )
                
            # Delete repository
            try:
                self.repo_service.delete_repository(repo_name)
            except RepoNotFoundError:
                pass
                
        except Exception as e:
            raise RuntimeModuleError(f"Failed to delete runtime module: {str(e)}")
            
    def create_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType
    ):
        """Create relationship between modules"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO module_relations
                    (source_id, target_id, relation_type, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        target_id,
                        relation_type.value,
                        datetime.utcnow().isoformat()
                    )
                )
        except Exception as e:
            raise RuntimeModuleError(f"Failed to create relation: {str(e)}")
            
    def delete_relation(self, source_id: str, target_id: str):
        """Delete relationship between modules"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM module_relations WHERE source_id = ? AND target_id = ?",
                    (source_id, target_id)
                )
        except Exception as e:
            raise RuntimeModuleError(f"Failed to delete relation: {str(e)}")
            
    def get_module_graph(self) -> nx.DiGraph:
        """Get NetworkX graph of module relationships"""
        graph = nx.DiGraph()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Add nodes
                modules = conn.execute("SELECT * FROM runtime_modules").fetchall()
                for module in modules:
                    graph.add_node(
                        module[0],  # id
                        module_id=module[1],
                        version=module[2],
                        created_at=module[3],
                        env_vars=eval(module[4]),
                        repo_name=module[5]
                    )
                
                # Add edges
                relations = conn.execute("SELECT * FROM module_relations").fetchall()
                for relation in relations:
                    graph.add_edge(
                        relation[0],  # source_id
                        relation[1],  # target_id
                        type=relation[2],
                        created_at=relation[3]
                    )
                    
            return graph
            
        except Exception as e:
            raise RuntimeModuleError(f"Failed to build module graph: {str(e)}")