from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Form
from fastapi.responses import JSONResponse
from pathlib import Path
import shutil
import zipfile
import os
from typing import List, Optional
from git import Actor, GitCommandError, Repo
from pydantic import BaseModel
import glob
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser, OrGroup
from whoosh.scoring import BM25F
from whoosh.analysis import StandardAnalyzer
import re
import whoosh.index as index
from datetime import datetime

from engine.utils.file import is_safe_path

def create_search_index(repo_path: Path, repo_name: str, search_index_dir: Path):
    """Create or update search index for a repository"""
    analyzer = StandardAnalyzer()
    schema = Schema(
        path=ID(stored=True),
        content=TEXT(stored=True, analyzer=analyzer),
        lines=STORED
    )
    
    if not search_index_dir.joinpath(repo_name).exists():
        search_index_dir.joinpath(repo_name).mkdir()
    
    ix = create_in(str(search_index_dir.joinpath(repo_name)), schema)
    writer = ix.writer()

    for file_path in repo_path.rglob("*"):
        if file_path.is_file() and not file_path.name.startswith('.'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.splitlines()
                    writer.add_document(
                        path=str(file_path.relative_to(repo_path)),
                        content=content,
                        lines=lines
                    )
            except Exception as e:
                print(f"Error indexing {file_path}: {str(e)}")
    
    writer.commit()
