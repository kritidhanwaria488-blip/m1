"""
Mutual Fund FAQ Assistant - Runtime Modules

This package contains all phase implementations for the RAG pipeline:
- phase_4_scrape: URL fetching and raw HTML storage
- phase_4_normalize: HTML cleaning and structured extraction
- phase_4_chunk_embed: Document chunking and embedding generation
- phase_4_index: Vector store indexing with ChromaDB
- phase_5_retrieval: Dense retrieval from vector store
- phase_6_generation: LLM answer generation with Groq
- phase_7_safety: Intent routing and safety validation
- phase_8_threads: Multi-thread conversation management
- phase_9_api: FastAPI application layer
"""

__version__ = "0.1.0"
__author__ = "Mutual Fund FAQ Assistant Team"
