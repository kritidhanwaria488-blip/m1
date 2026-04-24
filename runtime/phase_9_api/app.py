"""
Phase 9: FastAPI Application Layer

REST API endpoints for the RAG pipeline.
"""

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from runtime.phase_5_retrieval.retriever import ChromaRetriever
from runtime.phase_6_generation.generator import GroqGenerator
from runtime.phase_7_safety.validator import SafetyLayer
from runtime.phase_8_threads.storage import ThreadStorage

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Debug mode
DEBUG = os.getenv("RUNTIME_API_DEBUG", "1") == "1"

# Global instances
retriever: Optional[ChromaRetriever] = None
generator: Optional[GroqGenerator] = None
safety: Optional[SafetyLayer] = None
thread_storage: Optional[ThreadStorage] = None


class Pipeline:
    """Complete RAG pipeline integrating all phases."""
    
    def __init__(self):
        self.retriever = None
        self.generator = None
        self.safety = None
        self.thread_storage = None
    
    def initialize(self):
        """Initialize all pipeline components."""
        logger.info("Initializing RAG pipeline...")
        
        self.safety = SafetyLayer()
        logger.info("Safety layer initialized")
        
        self.retriever = ChromaRetriever()
        logger.info("Retriever initialized")
        
        try:
            self.generator = GroqGenerator()
            logger.info("Generator initialized")
        except ValueError as e:
            logger.warning(f"Generator not initialized (no GROQ_API_KEY): {e}")
        
        self.thread_storage = ThreadStorage()
        logger.info("Thread storage initialized")
        
        logger.info("Pipeline initialization complete")
    
    async def process_message(
        self,
        thread_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Process a user message through the full pipeline.
        
        Args:
            thread_id: Thread ID
            message: User message
        
        Returns:
            Response with assistant message and debug info
        """
        start_time = time.time()
        
        # Step 1: Safety check (Phase 7)
        safety_result = self.safety.check_input(message)
        if safety_result:
            return {
                "assistant_message": safety_result["message"],
                "debug": {
                    "retrieved_chunks": [],
                    "scores": [],
                    "safety_check": "refused",
                    "latency_ms": round((time.time() - start_time) * 1000, 2)
                } if DEBUG else None
            }
        
        # Step 2: Retrieve context (Phase 5)
        retrieval_start = time.time()
        chunks = self.retriever.retrieve_with_merging(message, top_k=5)
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        # Step 3: Generate answer (Phase 6) - if generator available
        generation_start = time.time()
        if self.generator:
            result = self.generator.generate(message, chunks)
            assistant_message = result.answer if not result.error else f"[Error: {result.error}]"
            citation_url = result.citation_url
            footer = result.footer
        else:
            # Fallback response without LLM
            if chunks:
                chunk = chunks[0]
                assistant_message = f"Based on {chunk.scheme_name}: {chunk.text[:200]}..."
                citation_url = chunk.source_url
                footer = f"Last updated: {chunk.fetched_at}"
            else:
                assistant_message = "I cannot find information about that in the indexed sources."
                citation_url = ""
                footer = ""
        
        generation_time = (time.time() - generation_start) * 1000
        total_time = (time.time() - start_time) * 1000
        
        # Step 4: Validate output (Phase 7)
        validation = self.safety.validate_output(assistant_message, citation_url)
        
        # Build response
        full_answer = f"{assistant_message}\n\nSource: {citation_url}\n\n{footer}".strip()
        
        response = {
            "assistant_message": full_answer,
            "debug": {
                "retrieved_chunks": [c.to_dict() for c in chunks] if DEBUG else len(chunks),
                "scores": [round(c.score, 4) for c in chunks] if DEBUG else [],
                "safety_check": "passed",
                "validation": validation.to_dict() if DEBUG else validation.is_valid,
                "retrieval_latency_ms": round(retrieval_time, 2),
                "generation_latency_ms": round(generation_time, 2),
                "latency_ms": round(total_time, 2)
            } if DEBUG else None
        }
        
        return response


# Global pipeline instance
pipeline = Pipeline()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting up API server...")
    pipeline.initialize()
    yield
    # Shutdown
    logger.info("Shutting down API server...")


# Create FastAPI app
app = FastAPI(
    title="Mutual Fund FAQ Assistant API",
    description="RAG-based API for factual mutual fund queries",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class CreateThreadRequest(BaseModel):
    session_key: Optional[str] = None


class CreateThreadResponse(BaseModel):
    thread_id: str
    session_key: str
    created_at: str


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    assistant_message: str
    debug: Optional[Dict[str, Any]] = None


class ThreadSummary(BaseModel):
    thread_id: str
    session_key: str
    created_at: str
    updated_at: str
    message_count: int


class HealthResponse(BaseModel):
    status: str
    version: str
    components: Dict[str, str]


# API Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "components": {
            "retriever": "ready" if pipeline.retriever else "not_ready",
            "generator": "ready" if pipeline.generator else "not_ready",
            "safety": "ready" if pipeline.safety else "not_ready",
            "threads": "ready" if pipeline.thread_storage else "not_ready"
        }
    }


@app.post("/threads", response_model=CreateThreadResponse)
async def create_thread(request: CreateThreadRequest):
    """
    Create a new isolated conversation thread.
    
    Each thread is completely independent with:
    - Unique UUID identifier
    - Isolated message history (no sharing with other threads)
    - Independent context for retrieval and generation
    
    Multiple threads can operate concurrently without interference.
    """
    if not pipeline.thread_storage:
        raise HTTPException(status_code=503, detail="Thread storage not initialized")
    
    thread = pipeline.thread_storage.create_thread(session_key=request.session_key)
    
    return {
        "thread_id": thread.thread_id,
        "session_key": thread.session_key,
        "created_at": thread.created_at
    }


@app.get("/threads", response_model=List[ThreadSummary])
async def list_threads(limit: int = 20):
    """List all conversation threads."""
    if not pipeline.thread_storage:
        raise HTTPException(status_code=503, detail="Thread storage not initialized")
    
    threads = pipeline.thread_storage.list_threads(limit=limit)
    return threads


@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    """Get thread details and messages."""
    if not pipeline.thread_storage:
        raise HTTPException(status_code=503, detail="Thread storage not initialized")
    
    thread = pipeline.thread_storage.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    return thread.to_dict()


@app.get("/threads/{thread_id}/messages")
async def get_messages(thread_id: str, limit: int = 50):
    """Get messages for a thread."""
    if not pipeline.thread_storage:
        raise HTTPException(status_code=503, detail="Thread storage not initialized")
    
    thread = pipeline.thread_storage.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    messages = thread.messages[-limit:] if limit else thread.messages
    return {
        "thread_id": thread_id,
        "messages": [m.to_dict() for m in messages]
    }


@app.post("/threads/{thread_id}/messages", response_model=MessageResponse)
async def post_message(
    thread_id: str,
    request: MessageRequest,
    background_tasks: BackgroundTasks
):
    """
    Post a message to a thread and get assistant response.
    
    This runs the full RAG pipeline:
    1. Safety check (Phase 7)
    2. Retrieve context (Phase 5)
    3. Generate answer (Phase 6)
    4. Validate output (Phase 7)
    """
    if not pipeline.thread_storage:
        raise HTTPException(status_code=503, detail="Thread storage not initialized")
    
    # Verify thread exists
    thread = pipeline.thread_storage.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Add user message
    pipeline.thread_storage.add_message(thread_id, "user", request.content)
    
    # Process through pipeline
    result = await pipeline.process_message(thread_id, request.content)
    
    # Add assistant response
    pipeline.thread_storage.add_message(
        thread_id,
        "assistant",
        result["assistant_message"],
        retrieval_debug_id=json.dumps(result.get("debug")) if DEBUG else None
    )
    
    return result


@app.post("/admin/reindex")
async def admin_reindex(
    secret: str = Header(..., alias="X-Admin-Secret")
):
    """Protected endpoint to trigger re-ingestion."""
    expected_secret = os.getenv("ADMIN_REINDEX_SECRET")
    
    if not expected_secret:
        raise HTTPException(status_code=501, detail="Admin secret not configured")
    
    if secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid secret")
    
    # In production, this would trigger the ingestion pipeline
    return {
        "status": "triggered",
        "message": "Re-ingestion scheduled (placeholder)"
    }


# Static files for basic UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Root endpoint - redirects to Next.js frontend or returns API info."""
    return {
        "message": "Mutual Fund FAQ Assistant API",
        "version": "1.0.0",
        "frontend": "http://localhost:3000 (Next.js)",
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "GET /health",
            "POST /threads",
            "GET /threads",
            "GET /threads/{id}",
            "GET /threads/{id}/messages",
            "POST /threads/{id}/messages"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
