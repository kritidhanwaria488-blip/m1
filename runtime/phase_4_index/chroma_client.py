"""
Phase 4.3: ChromaDB Local Client Module

Handles vector indexing using local ChromaDB (PersistentClient).
Stores vectors locally in data/chroma/ directory.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings

from runtime.phase_4_chunk_embed.chunker import Chunk

logger = logging.getLogger(__name__)


class ChromaIndex:
    """
    ChromaDB Local vector index manager.
    
    Uses local PersistentClient:
    - Embeddings: 384-dim (BGE-small)
    - Distance: Cosine similarity
    - Collection: mf_faq_chunks
    - Storage: Local filesystem (data/chroma/)
    """
    
    def __init__(
        self,
        collection_name: str = "mf_faq_chunks",
        embedding_dim: int = 384,
        persist_dir: Optional[str] = None
    ):
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        
        # Local storage directory
        self.persist_dir = persist_dir or os.getenv(
            "CHROMA_PERSIST_DIR",
            "data/chroma"
        )
        
        # Ensure directory exists
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize local ChromaDB client
        logger.info(f"Initializing local ChromaDB at: {self.persist_dir}")
        
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        logger.info("Connected to local ChromaDB successfully")
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "description": "Mutual Fund FAQ chunks with BGE embeddings"
            }
        )
        
        # Log collection stats
        count = self.collection.count()
        logger.info(
            f"Initialized ChromaIndex Local: collection={collection_name}, "
            f"dim={embedding_dim}, existing_docs={count}"
        )
    
    def upsert_chunks(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """
        Upsert chunks into ChromaDB.
        
        Uses chunk_id as the document ID for idempotent updates.
        
        Args:
            chunks: List of Chunk objects with embeddings
            
        Returns:
            Upsert result stats
        """
        if not chunks:
            logger.warning("No chunks to upsert")
            return {"upserted": 0}
        
        # Prepare batch data
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            if not chunk.embedding:
                logger.warning(f"Skipping chunk {chunk.chunk_id} - no embedding")
                continue
            
            ids.append(chunk.chunk_id)
            embeddings.append(chunk.embedding)
            documents.append(chunk.text)
            
            # Metadata for filtering
            metadatas.append({
                "scheme_id": chunk.scheme_id,
                "scheme_name": chunk.scheme_name,
                "amc": chunk.amc,
                "source_url": chunk.source_url,
                "source_type": chunk.source_type,
                "fetched_at": chunk.fetched_at,
                "content_hash": chunk.content_hash,
                "chunk_index": chunk.chunk_index,
                "section_title": chunk.section_title or "",
                "chunk_type": chunk.chunk_type,
                "token_count": chunk.token_count
            })
        
        if not ids:
            logger.warning("No valid chunks to upsert")
            return {"upserted": 0}
        
        # Perform upsert
        logger.info(f"Upserting {len(ids)} chunks to ChromaDB")
        
        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully upserted {len(ids)} chunks")
            return {
                "upserted": len(ids),
                "collection": self.collection_name
            }
            
        except Exception as e:
            logger.error(f"Failed to upsert chunks: {e}")
            raise
    
    def upsert_batch(
        self,
        chunks_by_scheme: Dict[str, List[Chunk]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Upsert chunks in batches by scheme.
        
        Args:
            chunks_by_scheme: Dict mapping scheme_id to list of Chunks
            batch_size: Number of chunks per batch
            
        Returns:
            Overall upsert stats
        """
        total_upserted = 0
        scheme_stats = []
        
        for scheme_id, chunks in chunks_by_scheme.items():
            logger.info(f"Upserting {len(chunks)} chunks for {scheme_id}")
            
            # Process in batches
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                result = self.upsert_chunks(batch)
                total_upserted += result["upserted"]
            
            scheme_stats.append({
                "scheme_id": scheme_id,
                "chunks": len(chunks)
            })
        
        return {
            "total_upserted": total_upserted,
            "schemes": len(chunks_by_scheme),
            "scheme_stats": scheme_stats
        }
    
    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Query the vector store.
        
        Args:
            query_embedding: 384-dim query vector
            n_results: Number of results to return
            where: Optional metadata filters
            
        Returns:
            Query results with documents, metadata, distances
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise
    
    def delete_by_scheme(self, scheme_id: str) -> int:
        """
        Delete all chunks for a scheme.
        
        Args:
            scheme_id: Scheme identifier to delete
            
        Returns:
            Number of deleted items
        """
        try:
            # Get all matching IDs first
            results = self.collection.get(
                where={"scheme_id": scheme_id}
            )
            
            if results and results["ids"]:
                ids_to_delete = results["ids"]
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} chunks for {scheme_id}")
                return len(ids_to_delete)
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to delete chunks for {scheme_id}: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "persist_dir": self.persist_dir,
                "total_documents": count,
                "embedding_dim": self.embedding_dim
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def get_index_manifest(self) -> Dict[str, Any]:
        """Get manifest of all indexed schemes."""
        try:
            # Get all documents
            results = self.collection.get(
                include=["metadatas"]
            )
            
            if not results or not results["metadatas"]:
                return {"schemes": [], "total_chunks": 0}
            
            # Count by scheme
            scheme_counts = {}
            for metadata in results["metadatas"]:
                scheme_id = metadata.get("scheme_id", "unknown")
                scheme_counts[scheme_id] = scheme_counts.get(scheme_id, 0) + 1
            
            return {
                "schemes": [
                    {"scheme_id": k, "chunks": v}
                    for k, v in scheme_counts.items()
                ],
                "total_chunks": len(results["metadatas"])
            }
            
        except Exception as e:
            logger.error(f"Failed to get manifest: {e}")
            return {}
