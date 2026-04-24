"""
Phase 4.2: Embedding Module

Generates vector embeddings using BAAI/bge-small-en-v1.5 model.
"""

import logging
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from runtime.phase_4_chunk_embed.chunker import Chunk

logger = logging.getLogger(__name__)


class BGEEmbedder:
    """
    Embedding generator using BAAI/bge-small-en-v1.5.
    
    Model specs:
    - Dimensions: 384
    - Max tokens: 512
    - Local inference (no API cost)
    - Same model for documents and queries (with query prefix)
    """
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        device: str = "cpu",
        batch_size: int = 32
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.dimensions = 384
        self.max_tokens = 512
        
        # BGE query prefix for asymmetric retrieval
        # Note: Only used at query time, not during indexing
        self.query_prefix = "Represent this sentence for searching relevant passages: "
        
        self._model: Optional[SentenceTransformer] = None
        
        logger.info(f"Initialized BGEEmbedder (model: {model_name}, device: {device})")
    
    def load_model(self) -> SentenceTransformer:
        """Load the embedding model (lazy loading)."""
        if self._model is None:
            logger.info(f"Loading model {self.model_name}...")
            self._model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Model loaded successfully")
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed (document chunk)
            
        Returns:
            384-dimensional embedding vector
        """
        model = self.load_model()
        
        # Truncate if needed (model handles this, but we log warnings)
        # Approximate token count
        estimated_tokens = len(text) // 4
        if estimated_tokens > self.max_tokens:
            logger.warning(
                f"Text may exceed max tokens ({estimated_tokens} > {self.max_tokens}), "
                f"truncating will occur"
            )
        
        # Generate embedding (no prefix for documents)
        embedding = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        
        return embedding.tolist()
    
    def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Embed multiple chunks in batches.
        
        Args:
            chunks: List of Chunk objects (text only, no embeddings yet)
            
        Returns:
            Chunks with embeddings populated
        """
        model = self.load_model()
        
        texts = [chunk.text for chunk in chunks]
        total = len(texts)
        
        logger.info(f"Embedding {total} chunks in batches of {self.batch_size}")
        
        # Process in batches
        all_embeddings = []
        
        for i in range(0, total, self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size
            
            logger.debug(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")
            
            # Generate embeddings for batch
            embeddings = model.encode(
                batch,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            
            all_embeddings.extend(embeddings.tolist())
            
            if batch_num % 10 == 0 or batch_num == total_batches:
                logger.info(f"Embedded {min(i + self.batch_size, total)}/{total} chunks")
        
        # Attach embeddings to chunks
        for chunk, embedding in zip(chunks, all_embeddings):
            chunk.embedding = embedding
        
        logger.info(f"Successfully embedded {len(chunks)} chunks")
        
        return chunks
    
    def embed_query(self, query: str) -> List[float]:
        """
        Embed a query string (with prefix for asymmetric retrieval).
        
        Args:
            query: User query text
            
        Returns:
            384-dimensional embedding vector
        """
        model = self.load_model()
        
        # Add query prefix for BGE asymmetric retrieval
        prefixed_query = f"{self.query_prefix}{query}"
        
        embedding = model.encode(
            prefixed_query,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        return embedding.tolist()
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "dimensions": self.dimensions,
            "max_tokens": self.max_tokens,
            "device": self.device,
            "batch_size": self.batch_size,
            "query_prefix": self.query_prefix,
            "loaded": self._model is not None
        }
