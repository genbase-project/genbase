import os
from typing import Dict, Generator, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import uuid
from loguru import logger

from haystack import Pipeline, Document
from haystack.components.writers import DocumentWriter
from haystack.components.embedders import SentenceTransformersTextEmbedder, SentenceTransformersDocumentEmbedder
from haystack.document_stores.types import DuplicatePolicy

# Import document stores
from haystack_integrations.document_stores.chroma import ChromaDocumentStore
from haystack_integrations.document_stores.pinecone import PineconeDocumentStore
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore
from haystack_integrations.document_stores.elasticsearch import ElasticsearchDocumentStore
from haystack_integrations.document_stores.opensearch import OpenSearchDocumentStore

# Import retrievers
from haystack_integrations.components.retrievers.chroma import ChromaQueryTextRetriever, ChromaEmbeddingRetriever
from haystack_integrations.components.retrievers.pinecone import PineconeEmbeddingRetriever
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.components.retrievers.weaviate import WeaviateEmbeddingRetriever
from haystack_integrations.components.retrievers.pgvector import PgvectorEmbeddingRetriever
from haystack_integrations.components.retrievers.elasticsearch import ElasticsearchEmbeddingRetriever
from haystack_integrations.components.retrievers.opensearch import OpenSearchEmbeddingRetriever
from engine.db.models import StoreType
@dataclass
class StoreConfig:
    env_vars: List[str]
    features: List[str]
    default_embedding_dim: int = 768
    priority: int = 0  # Lower number means higher priority
    embedder_model: str = "sentence-transformers/all-mpnet-base-v2"


STORE_CONFIGS = {
    StoreType.CHROMA: StoreConfig(
        env_vars=[],
        features=["embedding", "metadata_filtering"],
        priority=1
    ),
    StoreType.PINECONE: StoreConfig(
        env_vars=["PINECONE_API_KEY"],
        features=["embedding", "metadata_filtering", "namespace"],
        priority=2
    ),
    StoreType.QDRANT: StoreConfig(
        env_vars=["QDRANT_URL", "QDRANT_API_KEY"],
        features=["embedding", "sparse_embedding", "hybrid_search", "metadata_filtering"],
        priority=2
    ),
    StoreType.WEAVIATE: StoreConfig(
        env_vars=["WEAVIATE_URL", "WEAVIATE_API_KEY"],
        features=["embedding", "bm25", "metadata_filtering", "multi_modal"],
        priority=3
    ),
    StoreType.PGVECTOR: StoreConfig(
        env_vars=["PG_CONN_STR"],
        features=["embedding", "metadata_filtering", "keyword_search"],
        priority=3
    ),
    StoreType.ELASTICSEARCH: StoreConfig(
        env_vars=["ES_URL", "ES_USER", "ES_PASSWORD"],
        features=["embedding", "bm25", "metadata_filtering"],
        priority=4
    ),
    StoreType.OPENSEARCH: StoreConfig(
        env_vars=["OPENSEARCH_URL", "OPENSEARCH_USER", "OPENSEARCH_PASSWORD"],
        features=["embedding", "bm25", "metadata_filtering"],
        priority=4
    )
}
from engine.db.models import StoreType
from engine.services.storage.embedder import EmbeddingService
@dataclass
class VectorRecord:
    """Record structure for vector store"""
    content: str
    metadata: Dict[str, Any]
    id: Optional[str] = None
    created_at: datetime = datetime.utcnow()



class VectorStoreService:
    """Service for managing vector stores with consistent embedding model"""

    def __init__(
        self,
        embedding_service: EmbeddingService,  # Instance of EmbeddingService
        required_features: Optional[List[str]] = None,
        preferred_store: Optional[StoreType] = None,
        module_id: str = None,
        store_name: str = None,  # Added store_name parameter
        embedding_dim: int = None,
        **kwargs
    ):
        if not module_id:
            raise ValueError("module_id is required")
        if not embedding_service:
            raise ValueError("embedding_service is required")
        if not store_name:
            raise ValueError("store_name is required")
            
        self.module_id = module_id
        self.store_name = store_name
        self.embedding_service = embedding_service
        self.required_features = required_features or ["embedding"]
        self.embedding_dim = embedding_dim or STORE_CONFIGS[StoreType.CHROMA].default_embedding_dim
        
        # Select and create store
        self.store_type = self._select_store_type(preferred_store)
        self.config = STORE_CONFIGS[self.store_type]
        self.store = self._create_store(**kwargs)
        
        # Initialize writer component
        self.writer = DocumentWriter(document_store=self.store)
        
        logger.info(f"Initialized {self.store_type.value} store '{store_name}' for module {module_id}")

    def _check_feature_support(self, store_type: StoreType) -> bool:
        """Check if store supports all required features"""
        config = STORE_CONFIGS[store_type]
        return all(feature in config.features for feature in self.required_features)

    def _check_env_vars(self, store_type: StoreType) -> bool:
        """Check if all required environment variables are set"""
        config = STORE_CONFIGS[store_type]
        
        # If no env vars required, return True
        if not config.env_vars:
            return True
            
        # Check if env vars are a list or single string
        if isinstance(config.env_vars, list):
            return all(bool(os.getenv(var)) for var in config.env_vars)
        return bool(os.getenv(config.env_vars))

    def _get_available_stores(self) -> List[StoreType]:
        """Get list of available stores that meet requirements"""
        available_stores = []
        
        for store_type in StoreType:
            # Check both feature support and environment variables
            if self._check_feature_support(store_type) and self._check_env_vars(store_type):
                available_stores.append(store_type)
                
        return available_stores

    def _select_store_type(self, preferred_store: Optional[StoreType] = None) -> StoreType:
        """Select appropriate store type based on requirements and availability"""
        available_stores = self._get_available_stores()
        
        if not available_stores:
            raise ValueError(
                f"No available stores support required features: {self.required_features}"
            )

        if preferred_store and preferred_store in available_stores:
            return preferred_store

        # Sort by priority and select first
        return min(available_stores, key=lambda x: STORE_CONFIGS[x].priority)

    def _create_store(self, **kwargs) -> Any:
        """Create store instance with correct configuration"""
        base_kwargs = {
            "embedding_dim": self.embedding_dim,
        }
        base_kwargs.update(kwargs)

        stores = {
            StoreType.CHROMA: ChromaDocumentStore,
            StoreType.PINECONE: PineconeDocumentStore,
            StoreType.QDRANT: QdrantDocumentStore,
            StoreType.WEAVIATE: WeaviateDocumentStore,
            StoreType.PGVECTOR: PgvectorDocumentStore,
            StoreType.ELASTICSEARCH: ElasticsearchDocumentStore,
            StoreType.OPENSEARCH: OpenSearchDocumentStore
        }

        store_class = stores.get(self.store_type)
        if not store_class:
            raise ValueError(f"No implementation for store type: {self.store_type.value}")

        return store_class(**base_kwargs)

    def _to_document(self, record: VectorRecord, embedding: List[float]) -> Document:
        """Convert VectorRecord to Haystack Document with embedding"""
        metadata = {
            "module_id": self.module_id,
            "store_name": self.store_name,
            "created_at": record.created_at.isoformat(),
            **record.metadata
        }
        
        return Document(
            content=record.content,
            meta=metadata,
            id_=record.id or str(uuid.uuid4()),
            embedding=embedding
        )

    def _from_document(self, doc: Document) -> VectorRecord:
        """Convert Haystack Document to VectorRecord"""
        metadata = doc.meta.copy()
        metadata.pop("module_id", None)
        metadata.pop("store_name", None)
        created_at = metadata.pop("created_at", None)
        
        return VectorRecord(
            content=doc.content,
            metadata=metadata,
            id=doc.id_,
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.utcnow()
        )

    async def write_records(self, records: List[VectorRecord]) -> None:
        """Write records to store with embeddings from the embedding service"""
        documents = []
        for record in records:
            # Get embedding for the record
            embedding_response = await self.embedding_service.get_embedding(
                input=record.content
            )
            embedding_vector = embedding_response['data'][0]['embedding']
            
            # Create document with embedding
            document = self._to_document(record, embedding_vector)
            documents.append(document)
        
        # Use the writer component to write documents
        self.writer.run({"documents": documents})

    async def write_record(self, record: VectorRecord) -> None:
        """Write a single record to the store"""
        await self.write_records([record])

    async def query_records(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorRecord]:
        """Query records from store using embedding service"""
        # Initialize retriever based on store type
        retrievers = {
            StoreType.CHROMA: ChromaEmbeddingRetriever,
            StoreType.PINECONE: PineconeEmbeddingRetriever,
            StoreType.QDRANT: QdrantEmbeddingRetriever,
            StoreType.WEAVIATE: WeaviateEmbeddingRetriever,
            StoreType.PGVECTOR: PgvectorEmbeddingRetriever,
            StoreType.ELASTICSEARCH: ElasticsearchEmbeddingRetriever,
            StoreType.OPENSEARCH: OpenSearchEmbeddingRetriever
        }
        
        retriever_class = retrievers.get(self.store_type)
        if not retriever_class:
            raise ValueError(f"No retriever for store type: {self.store_type.value}")
            
        retriever = retriever_class(document_store=self.store)
        
        # Get query embedding
        embedding_response = await self.embedding_service.get_embedding(
            input=query
        )
        query_embedding = embedding_response['data'][0]['embedding']
        
        # Add module_id and store_name to filters
        query_filters = {
            "module_id": self.module_id,
            "store_name": self.store_name
        }
        if filters:
            query_filters.update(filters)
            
        # Use retriever to get documents
        results = retriever.run(
            query_embedding=query_embedding,
            filters=query_filters,
            top_k=top_k
        )
        
        return [self._from_document(doc) for doc in results["documents"]]

    def delete_documents(self, ids: Optional[List[str]] = None):
        """Delete documents from the store by ids or filters"""
            
        self.store.delete_documents(ids=ids)

    def get_document_count(self) -> int:
        """Get count of documents matching the filters"""

            
        return self.store.count_documents()

    def get_document_by_id(self, document_id: str) -> Optional[VectorRecord]:
        """Get a specific document by ID"""
        doc = self.store.get_document_by_id(document_id)
        if doc and doc.meta.get("module_id") == self.module_id and doc.meta.get("store_name") == self.store_name:
            return self._from_document(doc)
        return None

    def get_documents(
        self,
        ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 100
    ) -> Generator[VectorRecord, None, None]:
        """Get documents by IDs or filters with batching"""
        get_filters = {
            "module_id": self.module_id,
            "store_name": self.store_name
        }
        if filters:
            get_filters.update(filters)
            
        for doc_batch in self.store.get_documents_generator(
            ids=ids,
            filters=get_filters,
            batch_size=batch_size
        ):
            for doc in doc_batch:
                yield self._from_document(doc)

    def get_store_info(self) -> Dict[str, Any]:
        """Get information about the current store"""
        return {
            "store_type": self.store_type.value,
            "store_name": self.store_name,
            "features": STORE_CONFIGS[self.store_type].features,
            "required_features": self.required_features,
            "module_id": self.module_id,
            "embedding_dim": self.embedding_dim,
            "embedding_model": self.embedding_service.model_name,
            "document_count": self.get_document_count()
        }