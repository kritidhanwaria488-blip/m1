"""
Phase 4.3: Vector Index CLI

Upserts chunked embeddings into local ChromaDB.

Usage:
    python -m runtime.phase_4_index --run-id <RUN_ID>

Examples:
    python -m runtime.phase_4_index --run-id 20240115-091500
    python -m runtime.phase_4_index --run-id 20240115-091500 --persist-dir data/chroma --verbose
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from runtime.phase_4_chunk_embed.storage import ChunkedStorage
from runtime.phase_4_index.chroma_client import ChromaIndex

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 4.3: Index chunks to ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m runtime.phase_4_index --run-id 20240115-091500
  python -m runtime.phase_4_index --run-id 20240115-091500 --verbose
        """
    )
    
    parser.add_argument('--run-id', required=True, help='Run identifier from Phase 4.2')
    parser.add_argument('--input-dir', default='data/structured', help='Input chunked directory')
    parser.add_argument('--collection', default='mf_faq_chunks', help='Collection name')
    parser.add_argument('--batch-size', type=int, default=100, help='Upsert batch size')
    parser.add_argument('--persist-dir', default='data/chroma', help='ChromaDB persist directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 60)
    logger.info("Phase 4.3: Vector Index (Local ChromaDB)")
    logger.info("=" * 60)
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Collection: {args.collection}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Persist dir: {args.persist_dir}")
    
    # Initialize storage and index
    chunked_storage = ChunkedStorage(base_dir=args.input_dir)
    chroma_index = ChromaIndex(
        collection_name=args.collection,
        embedding_dim=384,  # BGE-small-en-v1.5
        persist_dir=args.persist_dir
    )
    
    # Load chunked manifest
    logger.info("Loading chunked manifest...")
    manifest = chunked_storage.load_manifest(args.run_id)
    
    if not manifest:
        logger.error(f"Chunked manifest not found for run {args.run_id}")
        sys.exit(1)
    
    logger.info(f"Found {manifest['total_chunks']} chunks from {manifest['total_schemes']} schemes")
    
    # Load all chunks
    logger.info("Loading chunks...")
    chunks_by_scheme = {}
    
    for file_info in manifest.get('files', []):
        scheme_id = file_info['scheme_id']
        chunks = chunked_storage.load_chunks(args.run_id, scheme_id)
        
        if chunks:
            chunks_by_scheme[scheme_id] = chunks
            logger.info(f"  Loaded {len(chunks)} chunks for {scheme_id}")
        else:
            logger.warning(f"  No chunks found for {scheme_id}")
    
    if not chunks_by_scheme:
        logger.error("No chunks loaded, cannot index")
        sys.exit(1)
    
    # Upsert to ChromaDB
    logger.info("=" * 60)
    logger.info("Upserting to ChromaDB...")
    logger.info("=" * 60)
    
    try:
        result = chroma_index.upsert_batch(
            chunks_by_scheme=chunks_by_scheme,
            batch_size=args.batch_size
        )
        
        total_upserted = result['total_upserted']
        logger.info(f"Successfully upserted {total_upserted} chunks")
        
    except Exception as e:
        logger.error(f"Failed to upsert chunks: {e}")
        sys.exit(1)
    
    # Get collection stats
    logger.info("=" * 60)
    logger.info("Collection Statistics")
    logger.info("=" * 60)
    
    stats = chroma_index.get_collection_stats()
    logger.info(f"Collection: {stats['collection_name']}")
    logger.info(f"Total documents: {stats['total_documents']}")
    logger.info(f"Embedding dim: {stats['embedding_dim']}")
    
    index_manifest = chroma_index.get_index_manifest()
    logger.info(f"Indexed schemes: {len(index_manifest.get('schemes', []))}")
    for scheme in index_manifest.get('schemes', []):
        logger.info(f"  {scheme['scheme_id']}: {scheme['chunks']} chunks")
    
    # Save index manifest locally (for reference, not the actual data)
    manifest_dir = Path(args.input_dir) / args.run_id / "chunked"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    index_manifest_path = manifest_dir / "index_manifest.json"
    
    final_manifest = {
        'run_id': args.run_id,
        'phase': '4.3',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'chroma_storage': 'local',
        'persist_dir': args.persist_dir,
        'collection': args.collection,
        'embedding_model': manifest.get('embedding_model', {}),
        'upserted': total_upserted,
        'collection_stats': stats,
        'index_manifest': index_manifest
    }
    
    try:
        with open(index_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(final_manifest, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved index manifest: {index_manifest_path}")
    except Exception as e:
        logger.warning(f"Failed to save index manifest: {e}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("Phase 4.3 Complete")
    logger.info("=" * 60)
    logger.info(f"Total chunks indexed: {total_upserted}")
    logger.info(f"Collection: {args.collection}")
    logger.info(f"Chroma Storage: Local ({args.persist_dir})")
    logger.info("=" * 60)
    
    # Final verification
    final_count = chroma_index.collection.count()
    logger.info(f"FINAL VERIFICATION - Collection count: {final_count}")


if __name__ == '__main__':
    main()
