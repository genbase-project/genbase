import zipfile
import networkx as nx
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import os
import re
from dataclasses import dataclass
from enum import Enum
import io
from pathlib import Path
from engine.utils.logging import logger
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
    project_id: str
    module_id: str
    owner: str
    version: str
    created_at: str
    env_vars: Dict[str, str]
    repo_name: str
    path: str

class RuntimeModuleService:
    """Service for managing runtime modules and their relationships"""
    
    def __init__(
        self,
        db_path: str,
        workspace_base: str,
        repo_service: RepoService
    ):
        self.db_path = db_path
        self.workspace_base = Path(workspace_base)
        self.repo_service = repo_service
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Runtime modules table without path
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runtime_modules (
                    id TEXT PRIMARY KEY,
                    module_id TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    env_vars TEXT NOT NULL,
                    repo_name TEXT NOT NULL
                )
            """)
            
            # Project module mappings table with path
            # Note: No uniqueness constraints on project_id or path as multiple modules
            # can share the same project and path
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_module_mappings (
                    project_id TEXT NOT NULL,
                    module_id TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, module_id),
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (module_id) REFERENCES runtime_modules(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS module_relations (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id, relation_type),
                    FOREIGN KEY (source_id) REFERENCES runtime_modules(id),
                    FOREIGN KEY (target_id) REFERENCES runtime_modules(id)
                )
            """)

    def _validate_path(self, path: str) -> bool:
        """
        Validate module path format (alphanumeric segments separated by dots)
        Example valid paths: "abc.123", "service.auth.v1", "backend.users"
        """
        path_pattern = r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$'
        return bool(re.match(path_pattern, path))

    def create_runtime_module(
        self,
        project_id: str,
        owner: str,
        module_id: str,
        version: str,
        env_vars: Dict[str, str],
        path: str
    ) -> RuntimeModuleMetadata:
        """Create runtime module with path"""
        if not self._validate_path(path):
            raise RuntimeModuleError("Invalid path format. Path must be alphanumeric segments separated by dots")
            
        runtime_id = str(uuid.uuid4())
        repo_name = f"runtime-{runtime_id}"
        created_at = datetime.utcnow().isoformat()
        
        try:
            # Get workspace path
            workspace_path = self.workspace_base / owner / module_id / version / "workspace"
            if not workspace_path.exists():
                raise RuntimeModuleError(f"Workspace not found for {owner}/{module_id} v{version}")

            # Create in-memory zip of workspace
            memory_zip = io.BytesIO()
            with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(workspace_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(workspace_path)
                        zipf.write(file_path, arcname)
            
            memory_zip.seek(0)
            
            # Create repository
            self.repo_service.create_repository(
                repo_name=repo_name,
                content_file=memory_zip,
                filename="workspace.zip",
                extract_func=extract_zip
            )
            
            # Save to database using transaction
            with sqlite3.connect(self.db_path) as conn:
                # Insert runtime module
                conn.execute(
                    """
                    INSERT INTO runtime_modules 
                    (id, module_id, owner, version, created_at, env_vars, repo_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        runtime_id,
                        module_id,
                        owner,
                        version,
                        created_at,
                        str(env_vars),
                        repo_name
                    )
                )
                
                # Create project module mapping
                conn.execute(
                    """
                    INSERT INTO project_module_mappings
                    (project_id, module_id, path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        runtime_id,
                        path,
                        created_at,
                        created_at
                    )
                )
            
            return RuntimeModuleMetadata(
                id=runtime_id,
                project_id=project_id,
                module_id=module_id,
                owner=owner,
                version=version,
                created_at=created_at,
                env_vars=env_vars,
                repo_name=repo_name,
                path=path
            )
            
        except Exception as e:
            # Cleanup on failure
            try:
                self.repo_service.delete_repository(repo_name)
            except:
                pass
            raise RuntimeModuleError(f"Failed to create runtime module: {str(e)}")

    def update_module_path(self, runtime_id: str, project_id: str, new_path: str):
        """Update module path in a project"""
        if not self._validate_path(new_path):
            raise RuntimeModuleError("Invalid path format. Path must be alphanumeric segments separated by dots")
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                updated_at = datetime.utcnow().isoformat()
                cursor = conn.execute(
                    """
                    UPDATE project_module_mappings
                    SET path = ?, updated_at = ?
                    WHERE module_id = ? AND project_id = ?
                    """,
                    (new_path, updated_at, runtime_id, project_id)
                )
                
                if cursor.rowcount == 0:
                    raise RuntimeModuleError("Module not found in specified project")
                    
        except Exception as e:
            raise RuntimeModuleError(f"Failed to update module path: {str(e)}")

    def get_project_modules(self, project_id: str) -> List[RuntimeModuleMetadata]:
        """Get all runtime modules for a project"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        m.id,
                        m.module_id,
                        m.owner,
                        m.version,
                        m.created_at,
                        m.env_vars,
                        m.repo_name,
                        pm.project_id,
                        pm.path
                    FROM runtime_modules m
                    JOIN project_module_mappings pm ON m.id = pm.module_id
                    WHERE pm.project_id = ?
                    """,
                    (project_id,)
                )
                
                modules = []
                for row in cursor.fetchall():
                    modules.append(RuntimeModuleMetadata(
                        id=row[0],
                        module_id=row[1],
                        owner=row[2],
                        version=row[3],
                        created_at=row[4],
                        env_vars=eval(row[5]),
                        repo_name=row[6],
                        project_id=row[7],
                        path=row[8]
                    ))
                
                return modules
                
        except Exception as e:
            raise RuntimeModuleError(f"Failed to get project modules: {str(e)}")

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
        
    def delete_relation(self, source_id: str, target_id: str, relation_type: RelationType):
        """Delete relationship between modules"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM module_relations
                    WHERE source_id = ? AND target_id = ? AND relation_type = ?
                    """,
                    (source_id, target_id, relation_type.value)
                )
        except Exception as e:
            raise RuntimeModuleError(f"Failed to delete relation: {str(e)}")

    def get_module_graph(self) -> nx.DiGraph:
        """Get NetworkX graph of module relationships"""
        graph = nx.MultiDiGraph()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get all modules with their project mappings
                modules = conn.execute("""
                    SELECT 
                        m.id,
                        m.module_id,
                        m.owner,
                        m.version,
                        m.created_at,
                        m.env_vars,
                        m.repo_name,
                        pm.project_id,
                        pm.path
                    FROM runtime_modules m
                    JOIN project_module_mappings pm ON m.id = pm.module_id
                """).fetchall()
                
                for module in modules:
                    node_data = {
                        "module_id": module[1],
                        "owner": module[2],
                        "version": module[3],
                        "created_at": module[4],
                        "env_vars": eval(module[5]),
                        "repo_name": module[6],
                        "project_id": module[7],
                        "path": module[8]
                    }
                    
                    graph.add_node(module[0], **node_data)
                
                # Add edges
                relations = conn.execute("""
                    SELECT source_id, target_id, relation_type, created_at 
                    FROM module_relations
                """).fetchall()
                
                for relation in relations:
                    graph.add_edge(
                        relation[0],
                        relation[1],
                        key=f"{relation[0]}_{relation[1]}_{relation[2]}",
                        type=relation[2],
                        created_at=relation[3]
                    )
                    
            return graph
            
        except Exception as e:
            raise RuntimeModuleError(f"Failed to build module graph: {str(e)}")

    def delete_runtime_module(self, runtime_id: str):
        """Delete runtime module and its project mappings"""
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
                
                # Delete project mappings
                conn.execute(
                    "DELETE FROM project_module_mappings WHERE module_id = ?",
                    (runtime_id,)
                )
                
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


    def get_linked_modules(
        self,
        module_id: str,
        relation_type: Optional[RelationType] = None,
        as_dependent: bool = False
    ) -> List[RuntimeModuleMetadata]:
        """
        Get modules linked to the specified module
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if relation_type == RelationType.CONTEXT:
                    # For context relations, use UNION to get both directions
                    query = """
                        SELECT DISTINCT
                            m.id,
                            m.module_id,
                            m.owner,
                            m.version,
                            m.created_at,
                            m.env_vars,
                            m.repo_name,
                            pm.project_id,
                            pm.path
                        FROM runtime_modules m
                        JOIN project_module_mappings pm ON m.id = pm.module_id
                        JOIN module_relations r ON r.source_id = m.id
                        WHERE r.target_id = ? AND r.relation_type = ?
                        
                        UNION
                        
                        SELECT DISTINCT
                            m.id,
                            m.module_id,
                            m.owner,
                            m.version,
                            m.created_at,
                            m.env_vars,
                            m.repo_name,
                            pm.project_id,
                            pm.path
                        FROM runtime_modules m
                        JOIN project_module_mappings pm ON m.id = pm.module_id
                        JOIN module_relations r ON r.target_id = m.id
                        WHERE r.source_id = ? AND r.relation_type = ?
                    """
                    params = [module_id, relation_type.value, module_id, relation_type.value]
                else:
                    # For dependency relations, maintain directional logic
                    query = """
                        SELECT DISTINCT
                            m.id,
                            m.module_id,
                            m.owner,
                            m.version,
                            m.created_at,
                            m.env_vars,
                            m.repo_name,
                            pm.project_id,
                            pm.path
                        FROM runtime_modules m
                        JOIN project_module_mappings pm ON m.id = pm.module_id
                        JOIN module_relations r ON 
                    """
                    
                    if as_dependent:
                        query += "r.source_id = m.id AND r.target_id = ?"
                    else:
                        query += "r.target_id = m.id AND r.source_id = ?"
                        
                    params = [module_id]
                    
                    if relation_type:
                        query += " AND r.relation_type = ?"
                        params.append(relation_type.value)
                
                cursor = conn.execute(query, params)
                
                modules = []
                for row in cursor.fetchall():
                    modules.append(RuntimeModuleMetadata(
                        id=row[0],
                        module_id=row[1],
                        owner=row[2],
                        version=row[3],
                        created_at=row[4],
                        env_vars=eval(row[5]),
                        repo_name=row[6],
                        project_id=row[7],
                        path=row[8]
                    ))
                    
                return modules
                    
        except Exception as e:
            raise RuntimeModuleError(f"Failed to get linked modules: {str(e)}")
        


    def get_module_metadata(self, runtime_id: str) -> RuntimeModuleMetadata:
        """
        Get metadata for a runtime module
        
        Args:
            runtime_id: Runtime module ID
            
        Returns:
            RuntimeModuleMetadata: Module metadata
            
        Raises:
            RuntimeModuleError: If module not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT 
                        m.id,
                        m.module_id,
                        m.owner,
                        m.version,
                        m.created_at,
                        m.env_vars,
                        m.repo_name,
                        pm.project_id,
                        pm.path
                    FROM runtime_modules m
                    JOIN project_module_mappings pm ON m.id = pm.module_id
                    WHERE m.id = ?
                    """,
                    (runtime_id,)
                )
                
                row = cursor.fetchone()
                if not row:
                    raise RuntimeModuleError(f"Runtime module {runtime_id} not found")
                    
                return RuntimeModuleMetadata(
                    id=row[0],
                    module_id=row[1],
                    owner=row[2],
                    version=row[3],
                    created_at=row[4],
                    env_vars=eval(row[5]),
                    repo_name=row[6],
                    project_id=row[7],
                    path=row[8]
                )
                    
        except Exception as e:
            raise RuntimeModuleError(f"Failed to get module metadata: {str(e)}")