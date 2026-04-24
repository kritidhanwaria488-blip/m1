"""
Phase 9: API Server Entry Point

Run the FastAPI application server.
"""

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start the API server."""
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info("=" * 60)
    logger.info("Phase 9: API Server Starting")
    logger.info("=" * 60)
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug: {os.getenv('RUNTIME_API_DEBUG', '1')}")
    logger.info("=" * 60)
    logger.info("Endpoints:")
    logger.info("  GET  /           - Web UI")
    logger.info("  GET  /health     - Health check")
    logger.info("  POST /threads    - Create thread")
    logger.info("  GET  /threads    - List threads")
    logger.info("  GET  /threads/{id}/messages - Get messages")
    logger.info("  POST /threads/{id}/messages - Send message")
    logger.info("=" * 60)
    
    uvicorn.run(
        "runtime.phase_9_api.app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    sys.exit(main())
