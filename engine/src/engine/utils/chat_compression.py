from typing import List, Dict, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import GPT2TokenizerFast
import faiss
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime
    importance: float = 1.0

class ChatCompressor:
    def __init__(self, max_tokens: int = 4096):
        # Initialize encoders
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')
        self.max_tokens = max_tokens
        
        # Initialize FAISS index with cosine similarity
        dimension = self.embedding_model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product for cosine similarity
        
        # Storage for messages and embeddings
        self.messages: List[Message] = []
        self.embeddings: List[np.ndarray] = []
        
        # Importance scoring parameters
        self.recency_weight = 0.3
        self.relevance_weight = 0.4
        self.importance_weight = 0.3

    def add_message(self, role: str, content: str, importance: float = 1.0):
        """Add a new message to the chat history"""
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(),
            importance=importance
        )
        
        # Get embedding
        embedding = self.embedding_model.encode([content])[0]
        embedding = embedding / np.linalg.norm(embedding)  # Normalize for cosine similarity
        
        # Add to storage
        self.messages.append(message)
        self.embeddings.append(embedding)
        
        # Update FAISS index
        self.index.add(np.array([embedding], dtype='float32'))

    def get_compressed_context(self, current_query: str, max_messages: int = 10) -> List[Message]:
        """Get compressed context based on relevance to current query"""
        if not self.messages:
            return []
            
        # Get query embedding
        query_embedding = self.embedding_model.encode([current_query])[0]
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Search similar messages
        k = min(max_messages * 2, len(self.messages))  # Get more candidates than needed
        scores, indices = self.index.search(
            np.array([query_embedding], dtype='float32'),
            k
        )
        
        # Calculate importance scores
        candidates = []
        now = datetime.now()
        for idx, similarity_score in zip(indices[0], scores[0]):
            message = self.messages[idx]
            
            # Calculate recency score (exponential decay)
            time_diff = (now - message.timestamp).total_seconds() / 3600  # hours
            recency_score = np.exp(-time_diff / 24)  # 24-hour half-life
            
            # Combined score
            total_score = (
                self.recency_weight * recency_score +
                self.relevance_weight * similarity_score +
                self.importance_weight * message.importance
            )
            
            candidates.append((message, total_score))
        
        # Sort by score and select top messages
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected_messages = [c[0] for c in candidates[:max_messages]]
        
        # Sort by timestamp to maintain conversation flow
        selected_messages.sort(key=lambda m: m.timestamp)
        
        return self._trim_to_max_tokens(selected_messages)

    def _trim_to_max_tokens(self, messages: List[Message]) -> List[Message]:
        """Trim messages to fit within token limit"""
        total_tokens = 0
        result = []
        
        for message in messages:
            tokens = len(self.tokenizer.encode(message.content))
            if total_tokens + tokens <= self.max_tokens:
                result.append(message)
                total_tokens += tokens
            else:
                break
                
        return result

# # Example usage
# def demo_chat_compression():
#     compressor = ChatCompressor(max_tokens=1000)
    
#     # Add some chat history
#     compressor.add_message("user", "What's the best way to learn Python?", importance=1.0)
#     compressor.add_message("assistant", "To learn Python effectively, start with the basics like variables, loops, and functions. Then practice with small projects.", importance=1.0)
#     compressor.add_message("user", "Can you recommend some project ideas?", importance=1.0)
#     compressor.add_message("assistant", "Here are some beginner-friendly Python projects: 1. Todo list app 2. Calculator 3. Weather app 4. Simple game", importance=0.8)
    
#     # Add some unrelated messages
#     for _ in range(10):
#         compressor.add_message("user", "This is an unrelated message about cats and dogs.", importance=0.5)
#         compressor.add_message("assistant", "Here's a response about pets and animals.", importance=0.5)
    
#     # Get compressed context for a new query about Python
#     current_query = "I want to start building a Python web application. Where should I begin?"
#     relevant_context = compressor.get_compressed_context(current_query, max_messages=5)
    
#     print(f"Query: {current_query}\n")
#     print("Relevant context messages:")
#     for msg in relevant_context:
#         print(f"\n{msg.role}: {msg.content}")
#         print(f"Importance: {msg.importance}")
#         print(f"Timestamp: {msg.timestamp}")

# if __name__ == "__main__":
#     demo_chat_compression()