"""
Phase 5: Retrieval Layer CLI

Usage:
    python -m runtime.phase_5_retrieval "What is the expense ratio?"
    python -m runtime.phase_5_retrieval "query" --scheme hdfc_elss_tax_saver
    python -m runtime.phase_5_retrieval "query" --top-k 10 --verbose
"""

import argparse
import json
import logging
import sys
from typing import Optional

from dotenv import load_dotenv

from runtime.phase_5_retrieval.retriever import ChromaRetriever

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 5: Dense retrieval from Chroma Cloud"
    )
    parser.add_argument(
        "query",
        help="Search query"
    )
    parser.add_argument(
        "--collection",
        default="mf_faq_chunks",
        help="Chroma collection name (default: mf_faq_chunks)"
    )
    parser.add_argument(
        "--scheme",
        dest="scheme_filter",
        help="Filter by scheme_id (e.g., hdfc_elss_tax_saver_direct_growth)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results (default: 5)"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        default=True,
        help="Merge chunks from same URL (default: True)"
    )
    parser.add_argument(
        "--no-merge",
        dest="merge",
        action="store_false",
        help="Disable URL merging"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("="*60)
    logger.info("Phase 5: Dense Retrieval")
    logger.info("="*60)
    logger.info(f"Query: {args.query}")
    logger.info(f"Collection: {args.collection}")
    logger.info(f"Top-k: {args.top_k}")
    if args.scheme_filter:
        logger.info(f"Scheme filter: {args.scheme_filter}")
    logger.info("="*60)
    
    try:
        # Initialize retriever
        retriever = ChromaRetriever(
            collection_name=args.collection,
            top_k=args.top_k
        )
        
        # Retrieve
        if args.merge:
            chunks = retriever.retrieve_with_merging(
                query=args.query,
                scheme_filter=args.scheme_filter,
                top_k=args.top_k
            )
        else:
            chunks = retriever.retrieve(
                query=args.query,
                scheme_filter=args.scheme_filter,
                top_k=args.top_k
            )
        
        # Output
        if args.json:
            output = {
                "query": args.query,
                "retrieved_count": len(chunks),
                "chunks": [c.to_dict() for c in chunks]
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"Retrieved {len(chunks)} chunks")
            print('='*60)
            
            for i, chunk in enumerate(chunks, 1):
                print(f"\n{i}. Score: {chunk.score:.4f}")
                print(f"   Scheme: {chunk.scheme_name}")
                print(f"   AMC: {chunk.amc}")
                print(f"   URL: {chunk.source_url}")
                print(f"   Fetched: {chunk.fetched_at}")
                print(f"   Text: {chunk.text[:200]}...")
        
        logger.info("="*60)
        logger.info("Retrieval complete")
        logger.info("="*60)
        
        return 0 if chunks else 1
        
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
