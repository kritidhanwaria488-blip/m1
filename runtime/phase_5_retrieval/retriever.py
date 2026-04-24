"""
Phase 5: Retrieval Layer

Dense retrieval from local ChromaDB vector store.
Uses BAAI/bge-small-en-v1.5 for query embedding.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved chunk with metadata."""
    chunk_id: str
    text: str
    score: float
    source_url: str
    scheme_id: str
    scheme_name: str
    amc: str
    source_type: str
    fetched_at: str
    chunk_index: int
    section_title: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "score": round(self.score, 4),
            "source_url": self.source_url,
            "scheme_name": self.scheme_name,
            "amc": self.amc,
            "fetched_at": self.fetched_at
        }


class ChromaRetriever:
    """
    Dense retriever using local ChromaDB.
    
    Query flow:
    1. Embed query with BGE-small (384-dim)
    2. Search local ChromaDB collection
    3. Return top-k chunks with metadata
    """
    
    def __init__(
        self,
        collection_name: str = "mf_faq_chunks",
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        top_k: int = 20,
        persist_dir: Optional[str] = None
    ):
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.top_k = top_k
        
        # Local storage directory
        self.persist_dir = persist_dir or os.getenv(
            "CHROMA_PERSIST_DIR",
            "data/chroma"
        )
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info("Embedding model loaded")
        
        # Initialize local ChromaDB client
        logger.info(f"Connecting to local ChromaDB at: {self.persist_dir}")
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"Connected to collection: {collection_name}")
    
    def embed_query(self, query: str) -> List[float]:
        """Embed the query text."""
        embedding = self.embedding_model.encode(query, convert_to_tensor=False)
        return embedding.tolist()
    
    def retrieve(
        self,
        query: str,
        scheme_filter: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: User query text
            scheme_filter: Optional scheme_id to filter results
            top_k: Number of results (default: self.top_k)
        
        Returns:
            List of RetrievedChunk objects
        """
        k = top_k or self.top_k
        
        # Embed query
        query_embedding = self.embed_query(query)
        
        # Build metadata filter
        where_filter = None
        if scheme_filter:
            where_filter = {"scheme_id": scheme_filter}
        
        # Query Chroma
        logger.info(f"Querying local ChromaDB: k={k}, filter={where_filter}")
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert to RetrievedChunk objects
        chunks = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                text = results["documents"][0][i] if results["documents"] else ""
                distance = results["distances"][0][i] if results["distances"] else 0.0
                
                # Convert distance to similarity score (cosine distance -> similarity)
                score = 1.0 - distance
                
                chunk = RetrievedChunk(
                    chunk_id=chunk_id,
                    text=text,
                    score=score,
                    source_url=metadata.get("source_url", ""),
                    scheme_id=metadata.get("scheme_id", ""),
                    scheme_name=metadata.get("scheme_name", ""),
                    amc=metadata.get("amc", ""),
                    source_type=metadata.get("source_type", ""),
                    fetched_at=metadata.get("fetched_at", ""),
                    chunk_index=metadata.get("chunk_index", 0),
                    section_title=metadata.get("section_title")
                )
                chunks.append(chunk)
        
        logger.info(f"Retrieved {len(chunks)} chunks")
        return chunks
    
    def retrieve_with_merging(
        self,
        query: str,
        scheme_filter: Optional[str] = None,
        top_k: int = 20
    ) -> List[RetrievedChunk]:
        """
        Retrieve and merge chunks from same source URL.
        
        If multiple chunks from the same URL score highly,
        merge them while keeping one citation.
        """
        # Retrieve more to allow for merging
        chunks = self.retrieve(query, scheme_filter, top_k=top_k * 2)
        
        # Group by source_url
        url_groups: Dict[str, List[RetrievedChunk]] = {}
        for chunk in chunks:
            if chunk.source_url not in url_groups:
                url_groups[chunk.source_url] = []
            url_groups[chunk.source_url].append(chunk)
        
        # Select best chunk from each URL (highest score)
        merged = []
        seen_urls = set()
        for chunk in chunks:
            if chunk.source_url not in seen_urls:
                # Get all chunks for this URL
                group = url_groups[chunk.source_url]
                # Use the highest scoring one
                best = max(group, key=lambda x: x.score)
                merged.append(best)
                seen_urls.add(chunk.source_url)
                
                if len(merged) >= top_k:
                    break
        
        logger.info(f"Merged to {len(merged)} unique sources")
        return merged[:top_k]


if __name__ == "__main__":
    # Test retrieval
    logging.basicConfig(level=logging.INFO)
    
    retriever = ChromaRetriever()
    
    test_queries = [
        "What is the expense ratio of HDFC ELSS Tax Saver?",
        "exit load for HDFC Equity fund",
        "minimum investment amount"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        chunks = retriever.retrieve_with_merging(query, top_k=5)
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n{i}. Score: {chunk.score:.4f} | {chunk.scheme_name}")
            print(f"   URL: {chunk.source_url}")
            print(f"   Text: {chunk.text[:150]}...")
