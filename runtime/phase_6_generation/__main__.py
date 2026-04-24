"""
Phase 6: Generation Layer CLI

Usage:
    python -m runtime.phase_6_generation "What is the expense ratio?"
    python -m runtime.phase_6_generation "query" --model llama-3.1-8b-instant
    python -m runtime.phase_6_generation "query" --temperature 0.2 --json
"""

import argparse
import json
import logging
import sys

from dotenv import load_dotenv

from runtime.phase_5_retrieval.retriever import ChromaRetriever
from runtime.phase_6_generation.generator import GroqGenerator

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 6: LLM Answer Generation (Groq API)"
    )
    parser.add_argument(
        "query",
        help="User question to answer"
    )
    parser.add_argument(
        "--model",
        default="llama-3.1-8b-instant",
        help="Groq model to use (default: llama-3.1-8b-instant)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Temperature for generation (default: 0.2)"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=200,
        help="Max tokens for response (default: 200)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve (default: 5)"
    )
    parser.add_argument(
        "--collection",
        default="mf_faq_chunks",
        help="Chroma collection name"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 60)
    logger.info("Phase 6: LLM Generation (Groq API)")
    logger.info("=" * 60)
    logger.info(f"Query: {args.query}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Temperature: {args.temperature}")
    logger.info("=" * 60)
    
    try:
        # Initialize retriever and generator
        logger.info("Initializing retriever...")
        retriever = ChromaRetriever(
            collection_name=args.collection,
            top_k=args.top_k
        )
        
        logger.info("Initializing generator...")
        generator = GroqGenerator(
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
        
        # Step 1: Retrieve context
        logger.info("=" * 60)
        logger.info("Step 1: Retrieving context...")
        logger.info("=" * 60)
        
        chunks = retriever.retrieve_with_merging(
            query=args.query,
            top_k=args.top_k
        )
        
        logger.info(f"Retrieved {len(chunks)} chunks")
        
        # Step 2: Generate answer
        logger.info("=" * 60)
        logger.info("Step 2: Generating answer...")
        logger.info("=" * 60)
        
        result = generator.generate(args.query, chunks)
        
        if result.error:
            logger.error(f"Generation failed: {result.error}")
            sys.exit(1)
        
        # Output
        if args.json:
            output = {
                "query": args.query,
                "retrieved_chunks": len(chunks),
                "generation": result.to_dict(),
                "context": [c.to_dict() for c in chunks[:3]]  # First 3 chunks
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n{'=' * 60}")
            print("ANSWER")
            print('=' * 60)
            print(f"\n{result.answer}")
            print(f"\nSource: {result.citation_url}")
            print(f"\n{result.footer}")
            print(f"\n{'=' * 60}")
            print(f"Generation time: {result.latency_ms:.0f}ms" if result.latency_ms else "")
            print(f"Retrieved {len(chunks)} chunks")
            print('=' * 60)
        
        logger.info("=" * 60)
        logger.info("Generation complete")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
